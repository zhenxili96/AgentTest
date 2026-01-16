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
        articles = self.search_engine.search_all(
            context.max_articles,
            theme=context.theme,
            keywords=context.keywords,
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

        prices = []
        for stock in limited_stocks:
            price_data = self.stock_fetcher.fetch_realtime_price(
                stock.get("symbol"),
                stock_type=stock.get("stock_type"),
            )
            if price_data:
                prices.append(price_data)

        summary = (
            f"识别 {len(combined_stocks)} 个相关标的，"
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
        """建议Agent：输出投资建议与可执行清单"""
        evidence = synthesis_result.get("evidence", [])
        avg_confidence = verification_result.get("avg_confidence", 0)
        verification_score = verification_result.get("verification_score", 0)

        market_summary = market_result.get("summary", "")
        market_snapshot = self._render_market_snapshot(market_result.get("prices", []))
        prompt = (
            f"你是投资顾问，请基于以下信息为{context.theme}主题生成投资建议。"
            "输出JSON，字段包含: outlook, actions(list), watchlist(list), risk_notes(list), "
            "confidence(0-1), signal(买入/卖出/观望), signal_probs({buy,sell,hold}概率且总和=1)。\n\n"
            f"风险偏好: {context.risk_profile}\n"
            f"投资周期: {context.horizon_days}天\n"
            f"验证评分: {verification_score}\n"
            f"摘要: {synthesis_result.get('summary')}\n\n"
            f"市场摘要: {market_summary}\n"
            f"行情快照:\n{market_snapshot}\n\n"
            f"证据：\n{self._render_evidence_text(evidence)}"
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
            return ai_payload

        outlook = "观望" if verification_score < 0.5 else "谨慎跟踪"
        if verification_score >= 0.75 and avg_confidence >= Config.MIN_CONFIDENCE_SCORE:
            outlook = "关注机会"

        fallback_signal, fallback_probs = self._build_signal_probabilities(verification_score)
        return {
            "source": "fallback",
            "outlook": outlook,
            "actions": [
                "建立跟踪清单并复核核心指标",
                "设定分批进场或止损的触发条件",
            ],
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
