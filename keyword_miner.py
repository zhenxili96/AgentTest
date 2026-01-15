"""关键词挖掘Agent模块 - 实时从市场挖掘能引发白银价格波动的关键词"""
from openai import OpenAI
from typing import List, Dict, Set, Optional, Any
from datetime import datetime, timedelta
from collections import Counter
import re
from config import Config
from database import db


class KeywordMiner:
    """关键词挖掘Agent类 - 使用AI分析市场数据，挖掘影响白银价格的关键词"""
    
    def __init__(self):
        # 初始化AI客户端（与ConfidenceEvaluator类似的逻辑）
        self.provider = Config.AI_PROVIDER
        self.api_key = None
        self.base_url = None
        self.model = "gpt-4o-mini"
        self.client = None
        
        if self.provider == "openrouter" and Config.OPENROUTER_API_KEY:
            self.api_key = Config.OPENROUTER_API_KEY
            self.base_url = "https://openrouter.ai/api/v1"
            # OpenRouter备用模型列表
            self.fallback_models = [
                "openai/gpt-4o-mini",
                "openai/gpt-3.5-turbo",
                "anthropic/claude-3-haiku",
                "google/gemini-pro",
                "meta-llama/llama-3.1-8b-instruct:free",
            ]
            # 如果配置了自定义模型，优先使用
            if Config.AI_MODEL:
                self.model = Config.AI_MODEL
            else:
                self.model = self.fallback_models[0]
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        elif Config.OPENAI_API_KEY:
            self.api_key = Config.OPENAI_API_KEY
            self.base_url = None
            # OpenAI备用模型列表
            self.fallback_models = [
                "gpt-4o-mini",
                "gpt-3.5-turbo",
                "gpt-4-mini",
            ]
            # 如果配置了自定义模型，优先使用
            if Config.AI_MODEL:
                self.model = Config.AI_MODEL
            else:
                self.model = self.fallback_models[0]
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.fallback_models = []
        
        # 现有的基础关键词（用于过滤和参考）
        self.base_keywords = set(Config.SEARCH_KEYWORDS)
    
    def mine_keywords_from_articles(
        self, 
        hours: int = 24, 
        min_confidence: float = 0.7,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """从高置信度文章中挖掘关键词"""
        if not self.client:
            print("⚠️ 未配置AI API，无法进行关键词挖掘")
            return []
        
        try:
            # 获取高置信度文章
            articles = db.get_high_confidence_articles(
                limit=limit,
                min_score=min_confidence
            )
            
            if not articles:
                print("⚠️ 没有找到高置信度文章，无法挖掘关键词")
                return []
            
            print(f"📊 分析 {len(articles)} 篇高置信度文章以挖掘关键词...")
            
            # 构建分析文本
            articles_text = self._build_articles_summary(articles)
            
            # 使用AI分析并提取关键词
            keywords = self._extract_keywords_with_ai(articles_text, articles)
            
            return keywords
        except Exception as e:
            print(f"❌ 关键词挖掘出错: {e}")
            return []
    
    def mine_keywords_from_market_trends(
        self,
        market_context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """从市场趋势中挖掘关键词（基于当前市场情况和新闻）"""
        if not self.client:
            print("⚠️ 未配置AI API，无法进行关键词挖掘")
            return []
        
        try:
            # 获取最近的文章数据作为市场上下文
            recent_articles = db.get_recent_articles(hours=48, limit=100)
            
            if not recent_articles:
                print("⚠️ 没有找到近期文章，无法分析市场趋势")
                return []
            
            # 构建市场趋势分析文本
            market_text = self._build_market_trends_summary(recent_articles)
            if market_context:
                market_text += f"\n\n额外市场信息：\n{market_context}"
            
            # 使用AI分析市场趋势并提取关键词
            keywords = self._extract_keywords_from_trends_with_ai(market_text)
            
            return keywords
        except Exception as e:
            print(f"❌ 市场趋势关键词挖掘出错: {e}")
            return []
    
    def analyze_keyword_relevance(
        self,
        keyword: str,
        context: Optional[str] = None
    ) -> Dict[str, any]:
        """分析单个关键词与白银价格的相关性"""
        if not self.client:
            return {
                "keyword": keyword,
                "relevance_score": 0.5,
                "impact": "unknown",
                "reasoning": "未配置AI API，无法分析"
            }
        
        try:
            prompt = f"""请分析以下关键词与白银价格的关联程度和潜在影响。

关键词: {keyword}
{('上下文: ' + context) if context else ''}

请评估：
1. 该关键词与白银价格的关联程度（0-1分）
2. 潜在影响方向（上涨/下跌/中性/不确定）
3. 影响机制和原因

请以以下格式返回：
关联程度: 0.XX
影响方向: [上涨/下跌/中性/不确定]
影响原因: [简要说明]
"""
            
            # 尝试调用AI API，如果失败则尝试备用模型
            models_to_try = [self.model] + [m for m in self.fallback_models if m != self.model]
            last_error = None
            
            for model_to_try in models_to_try:
                try:
                    response = self.client.chat.completions.create(
                        model=model_to_try,
                        messages=[
                            {
                                "role": "system",
                                "content": "你是一个专业的贵金属市场分析师，擅长分析各种因素对白银价格的影响。"
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        temperature=0.3,
                        max_tokens=300,
                    )
                    
                    analysis = response.choices[0].message.content
                    
                    # 如果成功，更新当前使用的模型
                    if model_to_try != self.model:
                        print(f"模型 {self.model} 不可用，已切换到 {model_to_try}")
                        self.model = model_to_try
                    
                    # 解析结果
                    relevance_score = self._extract_score_from_text(analysis)
                    impact = self._extract_impact_from_text(analysis)
                    
                    return {
                        "keyword": keyword,
                        "relevance_score": relevance_score,
                        "impact": impact,
                        "reasoning": analysis,
                        "analyzed_at": datetime.utcnow()
                    }
                except Exception as e:
                    last_error = e
                    error_str = str(e)
                    # 如果是403错误（模型不可用），尝试下一个模型
                    if "403" in error_str or "not available" in error_str.lower() or "region" in error_str.lower():
                        print(f"模型 {model_to_try} 在您的地区不可用，尝试下一个模型...")
                        continue
                    # 其他错误直接抛出
                    raise
            
            # 所有模型都失败了
            raise last_error if last_error else Exception("所有模型都不可用")
            
        except Exception as e:
            print(f"分析关键词相关性出错: {e}")
            error_msg = str(e)
            if "403" in error_msg or "not available" in error_msg.lower():
                error_msg = "模型在您的地区不可用，请尝试配置其他模型（通过AI_MODEL环境变量）"
            return {
                "keyword": keyword,
                "relevance_score": 0.5,
                "impact": "unknown",
                "reasoning": f"分析出错: {error_msg}"
            }
    
    def _build_articles_summary(self, articles) -> str:
        """构建文章摘要文本用于AI分析"""
        summary_parts = []
        summary_parts.append(f"以下是 {len(articles)} 篇高置信度的白银投资相关文章：\n")
        
        for i, article in enumerate(articles[:20], 1):  # 限制前20篇
            summary_parts.append(f"\n文章 {i}:")
            summary_parts.append(f"标题: {article.title}")
            summary_parts.append(f"来源: {article.source}")
            summary_parts.append(f"置信度: {article.confidence_score:.2f}")
            if article.content:
                content_preview = article.content[:300]  # 限制长度
                summary_parts.append(f"内容摘要: {content_preview}")
            if article.keywords:
                summary_parts.append(f"已有关键词: {article.keywords}")
        
        return "\n".join(summary_parts)
    
    def _build_market_trends_summary(self, articles) -> str:
        """构建市场趋势摘要文本"""
        # 按时间分组
        now = datetime.utcnow()
        recent_24h = [a for a in articles if (now - a.published_at).total_seconds() <= 86400]
        recent_48h = [a for a in articles if (now - a.published_at).total_seconds() <= 172800]
        
        summary_parts = []
        summary_parts.append(f"市场趋势分析（基于 {len(articles)} 篇近期文章）：\n")
        summary_parts.append(f"- 最近24小时: {len(recent_24h)} 篇文章")
        summary_parts.append(f"- 最近48小时: {len(recent_48h)} 篇文章\n")
        
        # 提取高频关键词
        all_keywords = []
        for article in articles:
            if article.keywords:
                all_keywords.extend([kw.strip() for kw in article.keywords.split(",")])
        
        keyword_freq = Counter(all_keywords)
        top_keywords = keyword_freq.most_common(20)
        
        summary_parts.append("高频关键词:")
        for kw, count in top_keywords:
            summary_parts.append(f"  - {kw}: {count}次")
        
        # 添加高置信度文章的主题
        high_conf_articles = [a for a in articles if a.is_high_confidence][:10]
        summary_parts.append("\n高置信度文章主题:")
        for article in high_conf_articles:
            summary_parts.append(f"  - {article.title[:80]}")
        
        return "\n".join(summary_parts)
    
    def _extract_keywords_with_ai(
        self,
        articles_text: str,
        articles: List
    ) -> List[Dict[str, Any]]:
        """使用AI从文章中提取关键词"""
        prompt = f"""请分析以下高置信度的白银投资相关文章，挖掘出能引发白银价格波动的关键词。

{articles_text}

任务：
1. 从这些文章中识别出可能影响白银价格的关键词、短语或概念
2. 包括但不限于：经济指标、政策事件、行业动态、市场情绪、技术术语等
3. 优先挖掘那些在文章中频繁出现但可能不在当前搜索关键词列表中的词汇
4. 考虑中英文关键词

请以以下格式返回，每个关键词一行：
关键词1 | 相关性分数(0-1) | 影响方向(上涨/下跌/中性) | 简要说明
关键词2 | 相关性分数 | 影响方向 | 简要说明
...

示例：
美联储加息 | 0.9 | 下跌 | 加息通常导致美元走强，压制贵金属价格
光伏产业需求 | 0.85 | 上涨 | 白银在光伏产业中的应用增长推动需求
"""
        
        try:
            # 尝试调用AI API，如果失败则尝试备用模型
            models_to_try = [self.model] + [m for m in self.fallback_models if m != self.model]
            last_error = None
            
            for model_to_try in models_to_try:
                try:
                    response = self.client.chat.completions.create(
                        model=model_to_try,
                        messages=[
                            {
                                "role": "system",
                                "content": "你是一个专业的贵金属市场分析专家，擅长从市场数据中识别影响价格的关键因素。"
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        temperature=0.4,
                        max_tokens=1500,
                    )
                    
                    result_text = response.choices[0].message.content
                    
                    # 如果成功，更新当前使用的模型
                    if model_to_try != self.model:
                        print(f"模型 {self.model} 不可用，已切换到 {model_to_try}")
                        self.model = model_to_try
                    
                    # 解析关键词
                    keywords = self._parse_keywords_from_text(result_text)
                    keywords = self._validate_keywords_with_ai(
                        keywords,
                        min_relevance=0.5
                    )
                    
                    # 过滤掉已有的基础关键词
                    new_keywords = [
                        kw for kw in keywords
                        if kw["keyword"].lower() not in [bkw.lower() for bkw in self.base_keywords]
                    ]
                    
                    print(f"✅ 成功挖掘出 {len(new_keywords)} 个新关键词（共 {len(keywords)} 个）")
                    
                    return new_keywords
                except Exception as e:
                    last_error = e
                    error_str = str(e)
                    # 如果是403错误（模型不可用），尝试下一个模型
                    if "403" in error_str or "not available" in error_str.lower() or "region" in error_str.lower():
                        print(f"模型 {model_to_try} 在您的地区不可用，尝试下一个模型...")
                        continue
                    # 其他错误直接抛出
                    raise
            
            # 所有模型都失败了
            raise last_error if last_error else Exception("所有模型都不可用")
            
        except Exception as e:
            print(f"AI提取关键词出错: {e}")
            return []
    
    def _extract_keywords_from_trends_with_ai(
        self,
        market_text: str
    ) -> List[Dict[str, Any]]:
        """使用AI从市场趋势中提取关键词"""
        prompt = f"""请基于以下市场趋势分析，识别出可能在未来影响白银价格波动的关键词和概念。

{market_text}

任务：
1. 识别当前市场热点和趋势
2. 预测可能影响白银价格的潜在因素和关键词
3. 包括新兴概念、政策变化、行业趋势等
4. 考虑中英文关键词

请以以下格式返回：
关键词1 | 相关性分数(0-1) | 影响方向(上涨/下跌/中性) | 简要说明
关键词2 | 相关性分数 | 影响方向 | 简要说明
...
"""
        
        try:
            # 尝试调用AI API，如果失败则尝试备用模型
            models_to_try = [self.model] + [m for m in self.fallback_models if m != self.model]
            last_error = None
            
            for model_to_try in models_to_try:
                try:
                    response = self.client.chat.completions.create(
                        model=model_to_try,
                        messages=[
                            {
                                "role": "system",
                                "content": "你是一个专业的市场趋势分析专家，擅长识别和预测影响贵金属价格的因素。"
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        temperature=0.5,
                        max_tokens=1500,
                    )
                    
                    result_text = response.choices[0].message.content
                    
                    # 如果成功，更新当前使用的模型
                    if model_to_try != self.model:
                        print(f"模型 {self.model} 不可用，已切换到 {model_to_try}")
                        self.model = model_to_try
                    
                    # 解析关键词
                    keywords = self._parse_keywords_from_text(result_text)
                    keywords = self._validate_keywords_with_ai(
                        keywords,
                        min_relevance=0.5
                    )
                    
                    print(f"✅ 从市场趋势中挖掘出 {len(keywords)} 个关键词")
                    
                    return keywords
                except Exception as e:
                    last_error = e
                    error_str = str(e)
                    # 如果是403错误（模型不可用），尝试下一个模型
                    if "403" in error_str or "not available" in error_str.lower() or "region" in error_str.lower():
                        print(f"模型 {model_to_try} 在您的地区不可用，尝试下一个模型...")
                        continue
                    # 其他错误直接抛出
                    raise
            
            # 所有模型都失败了
            raise last_error if last_error else Exception("所有模型都不可用")
            
        except Exception as e:
            print(f"AI提取趋势关键词出错: {e}")
            return []

    def _validate_keywords_with_ai(
        self,
        keywords: List[Dict[str, Any]],
        min_relevance: float
    ) -> List[Dict[str, Any]]:
        """使用AI对关键词进行二次校验，剔除无关项"""
        if not keywords:
            return []

        if not self.client:
            print("⚠️ 未配置AI API，跳过关键词校验")
            return keywords

        prompt_lines = []
        for kw in keywords:
            prompt_lines.append(
                f"{kw.get('keyword', '')} | 初始相关性:{kw.get('relevance_score', 0.5):.2f} | "
                f"方向:{kw.get('impact', '不确定')} | 说明:{kw.get('reasoning', '')}"
            )

        prompt = f"""请对以下关键词进行二次校验，判断其是否与白银价格波动相关，避免无关或噪声词。

关键词列表：
{chr(10).join(prompt_lines)}

请逐条给出结论，格式如下（每行一个关键词）：
关键词 | 保留/剔除 | 相关性分数(0-1) | 简要原因
"""

        try:
            models_to_try = [self.model] + [m for m in self.fallback_models if m != self.model]
            last_error = None

            for model_to_try in models_to_try:
                try:
                    response = self.client.chat.completions.create(
                        model=model_to_try,
                        messages=[
                            {
                                "role": "system",
                                "content": "你是一个贵金属市场分析助理，负责校验关键词的相关性。"
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        temperature=0.2,
                        max_tokens=1200,
                    )

                    result_text = response.choices[0].message.content

                    if model_to_try != self.model:
                        print(f"模型 {self.model} 不可用，已切换到 {model_to_try}")
                        self.model = model_to_try

                    validated = self._apply_keyword_validation_results(
                        keywords,
                        result_text,
                        min_relevance
                    )
                    print(f"✅ 关键词校验完成，保留 {len(validated)} / {len(keywords)}")
                    return validated
                except Exception as e:
                    last_error = e
                    error_str = str(e)
                    if "403" in error_str or "not available" in error_str.lower() or "region" in error_str.lower():
                        print(f"模型 {model_to_try} 在您的地区不可用，尝试下一个模型...")
                        continue
                    raise

            raise last_error if last_error else Exception("所有模型都不可用")
        except Exception as e:
            print(f"AI关键词校验出错: {e}")
            return keywords

    def _apply_keyword_validation_results(
        self,
        keywords: List[Dict[str, Any]],
        result_text: str,
        min_relevance: float
    ) -> List[Dict[str, Any]]:
        """应用AI校验结果并过滤关键词"""
        validation_map = {}
        for line in result_text.split("\n"):
            line = line.strip()
            if not line or "|" not in line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 3:
                continue
            keyword = parts[0]
            decision = parts[1].lower()
            score = self._extract_score_from_text(parts[2])
            reason = parts[3] if len(parts) > 3 else ""
            keep = any(flag in decision for flag in ["保留", "keep", "retain", "yes"])
            validation_map[keyword] = {
                "keep": keep,
                "score": score,
                "reason": reason
            }

        validated = []
        for kw in keywords:
            keyword = kw.get("keyword", "")
            validation = validation_map.get(keyword)
            if not validation:
                validated.append(kw)
                continue
            kw["validation_score"] = validation["score"]
            kw["validation_reasoning"] = validation["reason"]
            if validation["keep"] and validation["score"] >= min_relevance:
                validated.append(kw)
        return validated
    
    def _parse_keywords_from_text(self, text: str) -> List[Dict[str, any]]:
        """从AI返回的文本中解析关键词"""
        keywords = []
        lines = text.split("\n")
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or "|" not in line:
                continue
            
            try:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 3:
                    keyword = parts[0].strip()
                    if not keyword:
                        continue
                    
                    # 提取分数
                    relevance_score = self._extract_score_from_text(parts[1])
                    
                    # 提取影响方向
                    impact = self._extract_impact_from_text(parts[1] + " " + parts[2] if len(parts) > 2 else parts[1])
                    
                    # 提取说明
                    reasoning = parts[3] if len(parts) > 3 else parts[2] if len(parts) > 2 else ""
                    
                    keywords.append({
                        "keyword": keyword,
                        "relevance_score": relevance_score,
                        "impact": impact,
                        "reasoning": reasoning,
                        "mined_at": datetime.utcnow(),
                        "source": "ai_analysis"
                    })
            except Exception as e:
                continue  # 跳过无法解析的行
        
        return keywords
    
    def _extract_score_from_text(self, text: str) -> float:
        """从文本中提取0-1之间的分数"""
        # 查找0.XX格式的数字
        matches = re.findall(r"0?\.\d+", text)
        if matches:
            try:
                score = float(matches[0])
                return max(0.0, min(1.0, score))
            except:
                pass
        return 0.5
    
    def _extract_impact_from_text(self, text: str) -> str:
        """从文本中提取影响方向"""
        text_lower = text.lower()
        if any(word in text_lower for word in ["上涨", "上升", "涨", "increase", "rise", "up", "bullish"]):
            return "上涨"
        elif any(word in text_lower for word in ["下跌", "下降", "跌", "decrease", "fall", "down", "bearish"]):
            return "下跌"
        elif any(word in text_lower for word in ["中性", "neutral", "持平"]):
            return "中性"
        else:
            return "不确定"
    
    def get_suggested_keywords(
        self,
        min_relevance: float = 0.6,
        max_results: int = 50
    ) -> List[str]:
        """获取建议的关键词列表（简化版本，只返回关键词字符串）"""
        # 从文章中挖掘
        mined_keywords = self.mine_keywords_from_articles(hours=48, min_confidence=0.7, limit=50)
        
        # 从市场趋势中挖掘
        trend_keywords = self.mine_keywords_from_market_trends()
        
        # 合并并去重
        all_keywords = {}
        for kw in mined_keywords + trend_keywords:
            keyword = kw["keyword"]
            if keyword not in all_keywords or kw["relevance_score"] > all_keywords[keyword]["relevance_score"]:
                all_keywords[keyword] = kw
        
        # 过滤和排序
        filtered = [
            kw for kw in all_keywords.values()
            if kw["relevance_score"] >= min_relevance
        ]
        filtered.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # 返回关键词列表
        return [kw["keyword"] for kw in filtered[:max_results]]
