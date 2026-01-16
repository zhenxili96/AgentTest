"""多Agent协作的投资建议生成器"""
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
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
        synthesis_result = self._synthesis_agent(context, research_result, verification_result)
        recommendation_result = self._recommendation_agent(
            context,
            research_result,
            verification_result,
            keyword_result,
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
                "summary": "未获取到可验证的文章",
            }

        sources = [article.get("source") for article in articles if article.get("source")]
        source_diversity = len(set(sources))

        cutoff = datetime.utcnow() - timedelta(hours=48)
        recent_count = 0
        for article in articles:
            published_at = article.get("published_at")
            if isinstance(published_at, datetime) and published_at >= cutoff:
                recent_count += 1

        recent_ratio = recent_count / max(len(articles), 1)
        avg_confidence = sum(
            article.get("confidence_score", 0) for article in articles
        ) / max(len(articles), 1)

        source_score = min(1.0, source_diversity / max(Config.AGENT_MIN_SOURCES, 1))
        verification_score = (
            0.4 * avg_confidence + 0.3 * source_score + 0.3 * recent_ratio
        )

        summary = (
            f"来源覆盖 {source_diversity} 个媒体，平均置信度 {avg_confidence:.2f}，"
            f"近48小时文章占比 {recent_ratio:.0%}。"
        )

        return {
            "verification_score": round(verification_score, 3),
            "source_diversity": source_diversity,
            "recent_ratio": round(recent_ratio, 3),
            "avg_confidence": round(avg_confidence, 3),
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
        synthesis_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """建议Agent：输出投资建议与可执行清单"""
        evidence = synthesis_result.get("evidence", [])
        avg_confidence = verification_result.get("avg_confidence", 0)
        verification_score = verification_result.get("verification_score", 0)

        prompt = (
            f"你是投资顾问，请基于以下信息为{context.theme}主题生成投资建议。"
            "输出JSON，字段包含: outlook, actions(list), watchlist(list), risk_notes(list), confidence(0-1)。\n\n"
            f"风险偏好: {context.risk_profile}\n"
            f"投资周期: {context.horizon_days}天\n"
            f"验证评分: {verification_score}\n"
            f"摘要: {synthesis_result.get('summary')}\n\n"
            f"证据：\n{self._render_evidence_text(evidence)}"
        )

        ai_payload = self._call_llm_json(prompt)
        if ai_payload:
            ai_payload["source"] = "ai"
            ai_payload["confidence"] = ai_payload.get("confidence", verification_score)
            return ai_payload

        outlook = "观望" if verification_score < 0.5 else "谨慎跟踪"
        if verification_score >= 0.75 and avg_confidence >= Config.MIN_CONFIDENCE_SCORE:
            outlook = "关注机会"

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
            ],
            "confidence": round(verification_score, 2),
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
