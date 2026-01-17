"""多Agent协作的投资建议生成器"""
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import re
from typing import Any, Dict, List, Optional

from config import Config
from search_engine import SearchEngine
from confidence_evaluator import ConfidenceEvaluator
from keyword_miner import KeywordMiner
from stock_identifier import StockIdentifier
from stock_fetcher import StockFetcher
from database import db


@dataclass
class AgentContext:
    """多Agent协作上下文"""

    theme: str
    keywords: Optional[List[str]]
    risk_profile: str
    horizon_days: int
    max_articles: int


class MultiAgentOrchestrator:
    """多Agent协作流程：检索 -> 验证 -> 归因 -> 建议"""

    def __init__(self) -> None:
        self.search_engine = SearchEngine()
        self.evaluator = ConfidenceEvaluator()
        self.keyword_miner = KeywordMiner()
        self.stock_identifier = StockIdentifier()
        self.stock_fetcher = StockFetcher()

    def run(
        self,
        theme: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        risk_profile: str = "balanced",
        horizon_days: int = 30,
        max_articles: Optional[int] = None,
    ) -> Dict[str, Any]:
        """执行多Agent流程并生成投资建议"""
        context = AgentContext(
            theme=(theme or Config.DEFAULT_THEME).strip(),
            keywords=keywords,
            risk_profile=risk_profile,
            horizon_days=horizon_days,
            max_articles=max_articles or Config.AGENT_MAX_ARTICLES,
        )

        research_result = self._research_agent(context)
        verification_result = self._verification_agent(context, research_result)
        keyword_result = self._keyword_agent(context, research_result)
        market_result = self._market_agent(context, research_result, keyword_result)
        synthesis_result = self._synthesis_agent(context, research_result, verification_result)
        recommendation_result = self._recommendation_agent(
            context,
            research_result,
            verification_result,
            keyword_result,
            market_result,
            synthesis_result,
        )

        return {
            "context": {
                "theme": context.theme,
                "keywords": context.keywords,
                "risk_profile": context.risk_profile,
                "horizon_days": context.horizon_days,
                "max_articles": context.max_articles,
            },
            "research": research_result,
            "verification": verification_result,
            "keywords": keyword_result,
            "market": market_result,
            "synthesis": synthesis_result,
            "recommendation": recommendation_result,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _research_agent(self, context: AgentContext) -> Dict[str, Any]:
        """检索Agent：获取并评估文章"""
        # 如果没有提供关键词，从数据库获取活跃的挖掘关键词
        search_keywords = context.keywords
        if not search_keywords:
            active_keywords = db.get_mined_keywords(is_active=True, min_relevance=0.6, limit=30)
            if active_keywords:
                search_keywords = [kw.keyword for kw in active_keywords]
                print(f"使用 {len(search_keywords)} 个挖掘的关键词进行搜索")
        
        articles = self.search_engine.search_all(
            context.max_articles,
            theme=context.theme,
            keywords=search_keywords,
        )

        evaluated_articles: List[Dict[str, Any]] = []
        for article in articles:
            evaluation = self.evaluator.evaluate(article, theme=context.theme)
            article_data = {**article, **evaluation}
            db.add_article(article_data)
            evaluated_articles.append(article_data)

        evaluated_articles.sort(
            key=lambda item: item.get("confidence_score", 0),
            reverse=True,
        )

        return {
            "total_found": len(articles),
            "total_evaluated": len(evaluated_articles),
            "high_confidence": [
                article
                for article in evaluated_articles
                if article.get("confidence_score", 0) >= Config.MIN_CONFIDENCE_SCORE
            ],
            "articles": evaluated_articles,
        }

    def _verification_agent(
        self,
        context: AgentContext,
        research_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """验证Agent：交叉验证来源与时间"""
        articles = research_result.get("articles", [])
        if not articles:
            return {
                "verification_score": 0.0,
                "source_diversity": 0,
                "recent_ratio": 0.0,
                "avg_confidence": 0.0,
                "duplicate_ratio": 0.0,
                "summary": "未获取到可验证的文章",
            }

        sources = [article.get("source") for article in articles if article.get("source")]
        source_diversity = len(set(sources))

        cutoff = datetime.utcnow() - timedelta(hours=48)
        recent_count = 0
        normalized_titles = []
        for article in articles:
            published_at = self._normalize_published_at(article.get("published_at"))
            if isinstance(published_at, datetime) and published_at >= cutoff:
                recent_count += 1
            title = article.get("title") or ""
            normalized_titles.append(self._normalize_title(title))

        recent_ratio = recent_count / max(len(articles), 1)
        avg_confidence = sum(
            article.get("confidence_score", 0) for article in articles
        ) / max(len(articles), 1)
        unique_titles = len(set(normalized_titles)) if normalized_titles else 0
        duplicate_ratio = (len(normalized_titles) - unique_titles) / max(len(normalized_titles), 1)

        source_score = min(1.0, source_diversity / max(Config.AGENT_MIN_SOURCES, 1))
        verification_score = (
            0.4 * avg_confidence + 0.3 * source_score + 0.2 * recent_ratio + 0.1 * (1 - duplicate_ratio)
        )
        verification_score = min(max(verification_score, 0.0), 1.0)

        summary = (
            f"来源覆盖 {source_diversity} 个媒体，平均置信度 {avg_confidence:.2f}，"
            f"近48小时文章占比 {recent_ratio:.0%}，"
            f"标题重复占比 {duplicate_ratio:.0%}。"
        )

        return {
            "verification_score": round(verification_score, 3),
            "source_diversity": source_diversity,
            "recent_ratio": round(recent_ratio, 3),
            "avg_confidence": round(avg_confidence, 3),
            "duplicate_ratio": round(duplicate_ratio, 3),
            "summary": summary,
        }

    def _keyword_agent(
        self,
        context: AgentContext,
        research_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """关键词Agent：补充主题驱动因素"""
        if self.keyword_miner.client:
            keywords = self.keyword_miner.mine_keywords_from_articles(
                hours=48,
                min_confidence=Config.MIN_CONFIDENCE_SCORE,
                limit=30,
                theme=context.theme,
            )
            for keyword in keywords:
                db.add_mined_keyword(keyword)
            return {
                "source": "ai",
                "keywords": keywords,
            }

        fallback_keywords: List[str] = []
        for article in research_result.get("articles", []):
            keyword_text = article.get("keywords") or ""
            for keyword in [kw.strip() for kw in keyword_text.split(",") if kw.strip()]:
                fallback_keywords.append(keyword)

        return {
            "source": "fallback",
            "keywords": [
                {"keyword": keyword, "relevance_score": 0.5}
                for keyword in sorted(set(fallback_keywords))
            ],
        }

    def _market_agent(
        self,
        context: AgentContext,
        research_result: Dict[str, Any],
        keyword_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """市场Agent：识别相关标的并拉取行情快照"""
        if not self.stock_identifier.client:
            # 即使没有AI，也尝试从数据库获取之前识别的股票
            existing_stocks = db.get_identified_stocks(
                is_active=True,
                theme=context.theme,
                limit=Config.AGENT_MAX_STOCKS
            )
            if existing_stocks:
                stocks_data = [
                    {
                        "symbol": s.symbol,
                        "company_name": s.company_name,
                        "stock_type": s.stock_type or "us_stock",
                        "market": s.market,
                        "relevance": s.relevance,
                        "theme": s.theme,
                    }
                    for s in existing_stocks
                ]
                prices = []
                for stock in stocks_data[:Config.AGENT_MAX_STOCKS]:
                    price_data = self.stock_fetcher.fetch_realtime_price(
                        stock.get("symbol"),
                        stock_type=stock.get("stock_type"),
                    )
                    if price_data:
                        prices.append(price_data)
                
                return {
                    "source": "database",
                    "symbols": stocks_data,
                    "prices": prices,
                    "summary": f"从数据库获取 {len(stocks_data)} 个相关标的，已获取 {len(prices)} 条行情快照。",
                }
            
            return {
                "source": "unavailable",
                "symbols": [],
                "prices": [],
                "summary": "未配置AI API，无法识别相关标的",
            }

        keyword_list = [
            item.get("keyword")
            for item in keyword_result.get("keywords", [])
            if isinstance(item, dict) and item.get("keyword")
        ]
        stocks_from_keywords = self.stock_identifier.identify_stocks_from_keywords(
            keyword_list,
            theme=context.theme,
        )
        stocks_from_articles = self.stock_identifier.identify_stocks_from_articles(
            research_result.get("articles", []),
            theme=context.theme,
            limit=20,
        )

        combined_stocks = self._dedupe_stocks(stocks_from_keywords + stocks_from_articles)
        limited_stocks = combined_stocks[: Config.AGENT_MAX_STOCKS]
        
        # 保存识别的股票到数据库
        saved_count = 0
        for stock in limited_stocks:
            stock_data = {
                "symbol": stock.get("symbol"),
                "company_name": stock.get("company_name", stock.get("name", "")),
                "stock_type": stock.get("stock_type", "us_stock"),
                "market": stock.get("market", ""),
                "relevance": stock.get("relevance", ""),
                "theme": context.theme,
                "source": "multi_agent",
                "is_active": True,
            }
            if db.add_identified_stock(stock_data):
                saved_count += 1
        
        if saved_count > 0:
            print(f"  ✅ 保存 {saved_count} 个新识别的股票到数据库")

        prices = []
        for stock in limited_stocks:
            price_data = self.stock_fetcher.fetch_realtime_price(
                stock.get("symbol"),
                stock_type=stock.get("stock_type"),
            )
            if price_data:
                prices.append(price_data)

        # 按类型统计
        type_counts = {}
        for stock in combined_stocks:
            st = stock.get("stock_type", "unknown")
            type_counts[st] = type_counts.get(st, 0) + 1
        
        type_summary = ", ".join([f"{k}: {v}个" for k, v in type_counts.items()])
        
        summary = (
            f"识别 {len(combined_stocks)} 个相关标的（{type_summary}），"
            f"已获取 {len(prices)} 条行情快照。"
        )

        return {
            "source": "ai",
            "symbols": combined_stocks,
            "prices": prices,
            "summary": summary,
        }

    def _synthesis_agent(
        self,
        context: AgentContext,
        research_result: Dict[str, Any],
        verification_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """归因Agent：梳理主题驱动逻辑"""
        articles = research_result.get("articles", [])
        evidence = self._build_evidence(articles)

        prompt = (
            f"你是专业投资研究员，请基于以下信息，归纳{context.theme}投资主题的"
            "主要驱动因素、短期风险与潜在催化剂。"
            "请以JSON返回，字段包含: drivers(list), risks(list), catalysts(list), summary(string)。\n\n"
            f"验证摘要：{verification_result.get('summary')}\n\n"
            f"证据：\n{self._render_evidence_text(evidence)}"
        )

        ai_payload = self._call_llm_json(prompt)
        if ai_payload:
            return {
                "source": "ai",
                "evidence": evidence,
                **ai_payload,
            }

        fallback_summary = (
            f"基于 {len(evidence)} 条高置信度证据，{context.theme}主题的关注点集中在"
            f"{', '.join([item['title'] for item in evidence[:3]])}等信息。"
        )

        return {
            "source": "fallback",
            "summary": fallback_summary,
            "drivers": ["供需变化", "宏观利率", "风险情绪"],
            "risks": ["数据来源不足", "市场波动放大"],
            "catalysts": ["政策声明", "库存数据", "工业需求变化"],
            "evidence": evidence,
        }

    def _recommendation_agent(
        self,
        context: AgentContext,
        research_result: Dict[str, Any],
        verification_result: Dict[str, Any],
        keyword_result: Dict[str, Any],
        market_result: Dict[str, Any],
        synthesis_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """建议Agent：输出投资建议与可执行清单（含具体投资标的）"""
        evidence = synthesis_result.get("evidence", [])
        avg_confidence = verification_result.get("avg_confidence", 0)
        verification_score = verification_result.get("verification_score", 0)

        # 获取识别的股票信息
        identified_stocks = market_result.get("symbols", [])
        stock_prices = market_result.get("prices", [])
        
        market_summary = market_result.get("summary", "")
        market_snapshot = self._render_market_snapshot(stock_prices)
        stocks_detail = self._render_stocks_detail(identified_stocks, stock_prices)
        
        prompt = (
            f"你是投资顾问，请基于以下信息为{context.theme}主题生成投资建议。\n"
            "【重要】请在建议中明确给出具体的投资标的和股票代码，并为每个标的给出明确的操作信号。\n\n"
            "输出JSON，字段包含:\n"
            "- outlook: 整体展望\n"
            "- actions: 具体操作建议列表，每条建议需明确标注涉及的股票代码\n"
            "- investment_targets: 推荐的具体投资标的列表，每项必须包含:\n"
            "  * symbol: 股票代码\n"
            "  * name: 公司名称\n"
            "  * stock_type: 标的类型(us_stock/a_stock/futures/etf)\n"
            "  * signal: 明确的操作信号，只能是'买入'、'卖出'或'观望'之一\n"
            "  * signal_strength: 信号强度(强烈/中等/轻度)\n"
            "  * action: 具体操作建议(如'分批建仓'、'逢低买入'、'止盈减仓'等)\n"
            "  * reason: 给出该操作建议的原因\n"
            "  * target_price: 目标价位(可选)\n"
            "  * stop_loss: 止损价位(可选)\n"
            "  * position_suggestion: 仓位建议\n"
            "- watchlist: 关注清单\n"
            "- risk_notes: 风险提示列表\n"
            "- confidence: 0-1置信度\n"
            "- signal: 整体建议(买入/卖出/观望)\n"
            "- signal_probs: {buy, sell, hold}概率且总和=1\n\n"
            f"风险偏好: {context.risk_profile}\n"
            f"投资周期: {context.horizon_days}天\n"
            f"验证评分: {verification_score}\n"
            f"摘要: {synthesis_result.get('summary')}\n\n"
            f"市场摘要: {market_summary}\n\n"
            f"【已识别的相关投资标的】\n{stocks_detail}\n\n"
            f"【实时行情快照】\n{market_snapshot}\n\n"
            f"【证据来源】\n{self._render_evidence_text(evidence)}"
        )

        ai_payload = self._call_llm_json(prompt)
        if ai_payload:
            normalized_signal, normalized_probs = self._normalize_signal_data(
                ai_payload,
                verification_score,
            )
            ai_payload["source"] = "ai"
            ai_payload["confidence"] = ai_payload.get("confidence", verification_score)
            ai_payload["signal"] = normalized_signal
            ai_payload["signal_probs"] = normalized_probs
            
            # 确保 investment_targets 存在，如果AI没有返回则从识别的股票构建
            if "investment_targets" not in ai_payload or not ai_payload["investment_targets"]:
                ai_payload["investment_targets"] = self._build_investment_targets(
                    identified_stocks, stock_prices, context
                )
            
            # 添加完整的股票信息供前端展示
            ai_payload["identified_stocks"] = identified_stocks
            ai_payload["stock_prices"] = stock_prices
            
            return ai_payload

        outlook = "观望" if verification_score < 0.5 else "谨慎跟踪"
        if verification_score >= 0.75 and avg_confidence >= Config.MIN_CONFIDENCE_SCORE:
            outlook = "关注机会"

        fallback_signal, fallback_probs = self._build_signal_probabilities(verification_score)
        
        # 构建具体投资标的建议
        investment_targets = self._build_investment_targets(identified_stocks, stock_prices, context)
        
        return {
            "source": "fallback",
            "outlook": outlook,
            "actions": self._build_actionable_suggestions(identified_stocks, context),
            "investment_targets": investment_targets,
            "identified_stocks": identified_stocks,
            "stock_prices": stock_prices,
            "watchlist": [item.get("title") for item in evidence[:5]],
            "risk_notes": [
                "信息来源集中度较高时需谨慎",
                "关注宏观利率与美元走势变化",
                "注意已识别标的的流动性与相关性差异",
            ],
            "confidence": round(verification_score, 2),
            "signal": fallback_signal,
            "signal_probs": fallback_probs,
        }
    
    def _render_stocks_detail(
        self,
        stocks: List[Dict[str, Any]],
        prices: List[Dict[str, Any]],
    ) -> str:
        """渲染股票详情供AI分析"""
        if not stocks:
            return "暂无识别到的相关标的。"
        
        # 构建价格映射
        price_map = {p.get("symbol"): p for p in prices}
        
        lines = []
        for stock in stocks:
            symbol = stock.get("symbol", "")
            name = stock.get("company_name", stock.get("name", ""))
            stock_type = stock.get("stock_type", "us_stock")
            relevance = stock.get("relevance", "")
            market = stock.get("market", "")
            
            type_label = {
                "us_stock": "美股",
                "a_stock": "A股",
                "futures": "期货",
                "etf": "ETF",
            }.get(stock_type, stock_type)
            
            # 获取价格信息
            price_info = price_map.get(symbol, {})
            price = price_info.get("price", "N/A")
            change_percent = price_info.get("change_percent", "")
            
            price_text = f"价格: {price}"
            if change_percent:
                price_text += f" ({change_percent:+.2f}%)" if isinstance(change_percent, (int, float)) else f" ({change_percent})"
            
            line = f"- {symbol} ({name}) [{type_label}]"
            if market:
                line += f" 市场: {market}"
            line += f" | {price_text}"
            if relevance:
                line += f" | 关联性: {relevance}"
            
            lines.append(line)
        
        return "\n".join(lines)
    
    def _build_investment_targets(
        self,
        stocks: List[Dict[str, Any]],
        prices: List[Dict[str, Any]],
        context: AgentContext,
    ) -> List[Dict[str, Any]]:
        """构建具体投资标的建议，包含明确的买入/卖出/观望信号"""
        if not stocks:
            return []
        
        price_map = {p.get("symbol"): p for p in prices}
        targets = []
        
        for stock in stocks[:8]:  # 限制最多8个标的
            symbol = stock.get("symbol", "")
            if not symbol:
                continue
            
            stock_type = stock.get("stock_type", "us_stock")
            name = stock.get("company_name", stock.get("name", symbol))
            relevance = stock.get("relevance", "")
            
            # 获取价格信息
            price_info = price_map.get(symbol, {})
            current_price = price_info.get("price")
            change_percent = price_info.get("change_percent")
            
            # 根据风险偏好生成仓位建议
            position = self._suggest_position(context.risk_profile, stock_type)
            
            # 生成明确的操作信号和建议
            signal, signal_strength, action = self._generate_stock_signal(
                change_percent, context.risk_profile, stock_type
            )
            
            target = {
                "symbol": symbol,
                "name": name,
                "stock_type": stock_type,
                "market": stock.get("market", ""),
                "signal": signal,  # 明确的买入/卖出/观望信号
                "signal_strength": signal_strength,  # 信号强度
                "action": action,  # 具体操作建议
                "reason": relevance or f"与{context.theme}主题相关",
                "position_suggestion": position,
                "current_price": current_price,
                "change_percent": change_percent,
                "target_price": None,  # 由AI填充
                "stop_loss": None,  # 由AI填充
            }
            targets.append(target)
        
        return targets
    
    def _generate_stock_signal(
        self,
        change_percent: Optional[float],
        risk_profile: str,
        stock_type: str,
    ) -> tuple[str, str, str]:
        """根据价格变化和风险偏好生成操作信号"""
        # 默认观望
        signal = "观望"
        signal_strength = "中等"
        action = "关注走势"
        
        if change_percent is None:
            return signal, signal_strength, action
        
        # 根据风险偏好调整阈值
        buy_threshold = -3 if risk_profile == "aggressive" else -5 if risk_profile == "balanced" else -7
        sell_threshold = 5 if risk_profile == "aggressive" else 7 if risk_profile == "balanced" else 10
        
        if change_percent <= buy_threshold:
            signal = "买入"
            if change_percent <= buy_threshold - 3:
                signal_strength = "强烈"
                action = "明显超跌，可分批建仓"
            else:
                signal_strength = "中等"
                action = "逢低关注，可小仓试探"
        elif change_percent >= sell_threshold:
            signal = "卖出"
            if change_percent >= sell_threshold + 3:
                signal_strength = "强烈"
                action = "涨幅过大，建议止盈减仓"
            else:
                signal_strength = "中等"
                action = "已有获利，可考虑部分止盈"
        elif change_percent > 0:
            signal = "观望"
            signal_strength = "轻度"
            action = "趋势向好，等待回调再介入"
        else:
            signal = "观望"
            signal_strength = "轻度"
            action = "小幅回调，关注支撑位"
        
        # 期货风险更高，信号更谨慎
        if stock_type == "futures":
            if signal == "买入":
                action += "，期货杠杆高请严控仓位"
            elif signal == "卖出":
                action += "，期货波动大请及时止盈"
        
        return signal, signal_strength, action
    
    def _suggest_position(self, risk_profile: str, stock_type: str) -> str:
        """根据风险偏好和标的类型建议仓位"""
        position_map = {
            "conservative": {
                "us_stock": "建议仓位≤5%，分批建仓",
                "a_stock": "建议仓位≤5%，分批建仓",
                "futures": "不建议，风险较高",
                "etf": "建议仓位≤10%，适合定投",
            },
            "balanced": {
                "us_stock": "建议仓位5-10%，分2-3批建仓",
                "a_stock": "建议仓位5-10%，分2-3批建仓",
                "futures": "建议仓位≤3%，严格止损",
                "etf": "建议仓位10-15%，可定投",
            },
            "aggressive": {
                "us_stock": "建议仓位10-20%，可择机重仓",
                "a_stock": "建议仓位10-20%，可择机重仓",
                "futures": "建议仓位≤10%，设置止损",
                "etf": "建议仓位15-25%",
            },
        }
        return position_map.get(risk_profile, position_map["balanced"]).get(stock_type, "建议仓位5-10%")
    
    def _build_actionable_suggestions(
        self,
        stocks: List[Dict[str, Any]],
        context: AgentContext,
    ) -> List[str]:
        """构建可执行的操作建议（含具体标的）"""
        actions = []
        
        if stocks:
            # 按类型分组
            us_stocks = [s for s in stocks if s.get("stock_type") == "us_stock"]
            a_stocks = [s for s in stocks if s.get("stock_type") == "a_stock"]
            futures = [s for s in stocks if s.get("stock_type") == "futures"]
            etfs = [s for s in stocks if s.get("stock_type") == "etf"]
            
            if us_stocks:
                symbols = ", ".join([s.get("symbol", "") for s in us_stocks[:3]])
                actions.append(f"美股关注标的：{symbols}，建议分批建仓并设置止损位")
            
            if a_stocks:
                symbols = ", ".join([s.get("symbol", "") for s in a_stocks[:3]])
                actions.append(f"A股关注标的：{symbols}，关注盘中低吸机会")
            
            if futures:
                symbols = ", ".join([s.get("symbol", "") for s in futures[:2]])
                actions.append(f"期货标的：{symbols}，严格控制仓位，设置止损")
            
            if etfs:
                symbols = ", ".join([s.get("symbol", "") for s in etfs[:2]])
                actions.append(f"ETF标的：{symbols}，适合定投配置")
        
        # 通用建议
        actions.extend([
            "建立跟踪清单，关注以上标的的技术面突破信号",
            f"根据{context.risk_profile}风险偏好，合理分配仓位",
            f"设定{context.horizon_days}天内的目标价位和止损位",
        ])
        
        return actions

    def _build_evidence(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """整理证据列表"""
        evidence: List[Dict[str, Any]] = []
        for article in articles[: Config.AGENT_TOP_EVIDENCE_COUNT]:
            published_at = article.get("published_at")
            if isinstance(published_at, datetime):
                published_at = published_at.isoformat()
            evidence.append(
                {
                    "title": article.get("title"),
                    "source": article.get("source"),
                    "url": article.get("url"),
                    "published_at": published_at,
                    "confidence_score": article.get("confidence_score"),
                }
            )
        return evidence

    def _render_evidence_text(self, evidence: List[Dict[str, Any]]) -> str:
        lines = []
        for item in evidence:
            lines.append(
                f"- {item.get('title')} ({item.get('source')}) {item.get('published_at')}, 置信度 {item.get('confidence_score')}"
            )
        return "\n".join(lines)

    def _render_market_snapshot(self, prices: List[Dict[str, Any]]) -> str:
        if not prices:
            return "暂无行情快照。"

        lines = []
        for item in prices:
            symbol = item.get("symbol", "")
            price = item.get("price", "N/A")
            change = item.get("change", "N/A")
            change_percent = item.get("change_percent", "")
            source = item.get("source", "")
            lines.append(f"- {symbol}: {price} ({change} / {change_percent}) 来源: {source}")
        return "\n".join(lines)

    def _normalize_signal_data(
        self,
        payload: Dict[str, Any],
        verification_score: float,
    ) -> tuple[str, Dict[str, float]]:
        signal = payload.get("signal")
        if isinstance(signal, str):
            normalized_signal = signal.strip().lower()
            if normalized_signal in {"buy", "bullish", "买入"}:
                signal = "买入"
            elif normalized_signal in {"sell", "bearish", "卖出"}:
                signal = "卖出"
            elif normalized_signal in {"hold", "neutral", "观望"}:
                signal = "观望"

        probabilities = self._extract_signal_probs(payload)
        if not probabilities:
            signal, probabilities = self._build_signal_probabilities(verification_score)

        normalized_probs = self._normalize_probabilities(probabilities)
        if signal not in {"买入", "卖出", "观望"}:
            signal = self._signal_from_probabilities(normalized_probs)
        return signal, normalized_probs

    def _extract_signal_probs(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        candidates = [
            payload.get("signal_probs"),
            payload.get("signal_probabilities"),
            payload.get("probabilities"),
        ]
        for candidate in candidates:
            if isinstance(candidate, dict):
                return candidate

        explicit = {}
        for key, normalized in {
            "buy": ["buy", "buy_prob", "buy_probability", "prob_buy"],
            "sell": ["sell", "sell_prob", "sell_probability", "prob_sell"],
            "hold": ["hold", "hold_prob", "hold_probability", "prob_hold", "neutral"],
        }.items():
            for option in normalized:
                value = payload.get(option)
                if isinstance(value, (int, float)):
                    explicit[key] = value
                    break
        return explicit or None

    def _normalize_probabilities(self, probs: Dict[str, Any]) -> Dict[str, float]:
        buy = self._coerce_probability(probs.get("buy"))
        sell = self._coerce_probability(probs.get("sell"))
        hold = self._coerce_probability(probs.get("hold"))

        total = sum(value for value in [buy, sell, hold] if value is not None)
        if total <= 0:
            return {"buy": 0.33, "sell": 0.33, "hold": 0.34}

        if buy is None:
            buy = 0.0
        if sell is None:
            sell = 0.0
        if hold is None:
            hold = 0.0

        normalized = {
            "buy": buy / total,
            "sell": sell / total,
            "hold": hold / total,
        }
        return normalized

    def _signal_from_probabilities(self, probs: Dict[str, float]) -> str:
        if probs["buy"] >= probs["sell"] and probs["buy"] >= probs["hold"]:
            return "买入"
        if probs["sell"] >= probs["buy"] and probs["sell"] >= probs["hold"]:
            return "卖出"
        return "观望"

    def _build_signal_probabilities(
        self,
        verification_score: float,
    ) -> tuple[str, Dict[str, float]]:
        base = min(max(verification_score, 0.0), 1.0)
        buy = 0.2 + 0.6 * base
        sell = 0.1 + 0.5 * (1 - base)
        hold = max(0.0, 1 - buy - sell)
        probs = self._normalize_probabilities({"buy": buy, "sell": sell, "hold": hold})
        return self._signal_from_probabilities(probs), probs

    @staticmethod
    def _coerce_probability(value: Any) -> Optional[float]:
        if isinstance(value, (int, float)):
            return min(max(float(value), 0.0), 1.0)
        return None

    @staticmethod
    def _normalize_title(title: str) -> str:
        normalized = re.sub(r"\s+", " ", title.strip().lower())
        normalized = re.sub(r"[^\w\u4e00-\u9fff]+", "", normalized)
        return normalized

    def _normalize_published_at(self, published_at: Any) -> Optional[datetime]:
        if isinstance(published_at, datetime):
            return published_at
        if isinstance(published_at, str):
            try:
                return datetime.fromisoformat(published_at.replace("Z", "+00:00"))
            except ValueError:
                pass
            try:
                return datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%S%z")
            except ValueError:
                return None
        return None

    @staticmethod
    def _dedupe_stocks(stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        deduped = []
        seen = set()
        for stock in stocks:
            symbol = stock.get("symbol")
            stock_type = stock.get("stock_type")
            if not symbol:
                continue
            key = (symbol, stock_type)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(stock)
        return deduped

    def _call_llm_json(self, prompt: str) -> Optional[Dict[str, Any]]:
        """调用AI并尝试解析JSON"""
        response_text = self._call_llm(prompt)
        if not response_text:
            return None

        json_text = self._extract_json(response_text)
        if not json_text:
            return None
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            return None

    def _call_llm(self, prompt: str) -> Optional[str]:
        """调用AI模型"""
        if not self.evaluator.client:
            return None

        models_to_try = [self.evaluator.model] + [
            model
            for model in self.evaluator.fallback_models
            if model != self.evaluator.model
        ]
        last_error = None
        for model_to_try in models_to_try:
            try:
                response = self.evaluator.client.chat.completions.create(
                    model=model_to_try,
                    messages=[
                        {
                            "role": "system",
                            "content": "你是专业投资研究员，请输出结构化JSON。",
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                    temperature=0.3,
                    max_tokens=800,
                )
                if model_to_try != self.evaluator.model:
                    self.evaluator.model = model_to_try
                return response.choices[0].message.content
            except Exception as exc:
                last_error = exc
                error_text = str(exc)
                if "403" in error_text or "not available" in error_text.lower():
                    continue
                break

        print(f"⚠️ AI调用失败：{last_error}")
        return None

    def _extract_json(self, text: str) -> Optional[str]:
        """从文本中提取JSON片段"""
        if not text:
            return None
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        return text[start : end + 1]
