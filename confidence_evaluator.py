"""AI置信度评估模块"""
from openai import OpenAI
from typing import Dict, Optional
from config import Config


class ConfidenceEvaluator:
    """使用AI模型评估信息的置信度（支持OpenAI和OpenRouter）"""
    
    def __init__(self):
        # 优先使用OpenRouter（如果配置了），否则使用OpenAI
        self.provider = Config.AI_PROVIDER
        self.api_key = None
        self.base_url = None
        self.model = "gpt-4o-mini"  # 默认模型
        
        # 定义备用模型列表（按优先级排序）
        if self.provider == "openrouter" and Config.OPENROUTER_API_KEY:
            self.api_key = Config.OPENROUTER_API_KEY
            self.base_url = "https://openrouter.ai/api/v1"
            # OpenRouter备用模型列表（如果主模型不可用，会依次尝试）
            self.fallback_models = [
                "openai/gpt-4o-mini",
                "xiaomi/mimo-v2-flash:free",
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
            self.base_url = None  # 使用OpenAI默认base_url
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
            self.client = None
            self.fallback_models = []
        
        self.min_confidence = Config.MIN_CONFIDENCE_SCORE
    
    def evaluate(self, article: Dict) -> Dict:
        """评估文章的可信度和相关性"""
        if not self.client:
            # 如果没有配置AI API，返回默认值
            provider_name = "OpenRouter或OpenAI" if self.provider == "openrouter" else "OpenAI"
            return {
                "confidence_score": 0.5,
                "relevance_score": 0.5,
                "reliability_score": 0.5,
                "ai_analysis": f"未配置{provider_name} API，无法进行AI评估",
                "is_high_confidence": False,
            }
        
        try:
            # 构建评估提示
            prompt = self._build_evaluation_prompt(article)
            
            # 尝试调用AI API，如果失败则尝试备用模型
            models_to_try = [self.model] + [m for m in self.fallback_models if m != self.model]
            last_error = None
            
            for model_to_try in models_to_try:
                try:
                    # 调用AI API（OpenAI或OpenRouter）
                    response = self.client.chat.completions.create(
                        model=model_to_try,
                        messages=[
                            {
                                "role": "system",
                                "content": "你是一个专业的金融信息分析专家，专门评估白银投资相关的新闻和信息源的可信度。"
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        temperature=0.3,
                        max_tokens=500,
                    )
                    
                    analysis_text = response.choices[0].message.content
                    
                    # 如果成功，更新当前使用的模型
                    if model_to_try != self.model:
                        print(f"模型 {self.model} 不可用，已切换到 {model_to_try}")
                        self.model = model_to_try
                    
                    # 解析评估结果
                    scores = self._parse_scores(analysis_text, article)
                    
                    is_high_confidence = scores["confidence_score"] >= self.min_confidence
                    
                    return {
                        **scores,
                        "ai_analysis": analysis_text,
                        "is_high_confidence": is_high_confidence,
                    }
                except Exception as e:
                    last_error = e
                    error_str = str(e)
                    # 如果是403错误（模型不可用），尝试下一个模型
                    if "403" in error_str or "not available" in error_str.lower() or "region" in error_str.lower():
                        print(f"模型 {model_to_try} 在您的地区不可用，尝试下一个模型...[{e}]")
                        continue
                    # 其他错误直接抛出
                    raise
            
            # 所有模型都失败了
            raise last_error if last_error else Exception("所有模型都不可用")
            
        except Exception as e:
            print(f"AI评估出错: {e}")
            # 返回默认评估
            error_msg = str(e)
            if "403" in error_msg or "not available" in error_msg.lower():
                error_msg = "模型在您的地区不可用，请尝试配置其他模型（通过AI_MODEL环境变量）"
            return {
                "confidence_score": 0.5,
                "relevance_score": 0.5,
                "reliability_score": 0.5,
                "ai_analysis": f"评估出错: {error_msg}",
                "is_high_confidence": False,
            }
    
    def _build_evaluation_prompt(self, article: Dict) -> str:
        """构建评估提示"""
        title = article.get("title", "")
        content = article.get("content", "")[:1000]  # 限制长度
        source = article.get("source", "")
        
        prompt = f"""
请评估以下关于白银投资的新闻文章的可信度和相关性。

标题: {title}
来源: {source}
内容摘要: {content}

请从以下三个维度进行评估（每个维度0-1分）：
1. 相关性（relevance_score）：文章与白银投资的关联程度
2. 可靠性（reliability_score）：信息来源的可靠性和可信度
3. 置信度（confidence_score）：综合置信度，用于投资决策的参考价值

请以以下格式返回评估结果：
相关性分数: 0.XX
可靠性分数: 0.XX
置信度分数: 0.XX
分析说明: [简要说明评估理由和文章的关键信息]

注意：置信度分数应该是相关性和可靠性的综合评估，通常取两者的平均值或加权平均。
"""
        return prompt
    
    def _parse_scores(self, analysis_text: str, article: Dict) -> Dict:
        """从AI分析文本中解析分数"""
        # 默认分数
        relevance_score = 0.5
        reliability_score = 0.5
        confidence_score = 0.5
        
        try:
            # 简单的正则提取（可以改进）
            lines = analysis_text.split("\n")
            for line in lines:
                line_lower = line.lower()
                if "相关性" in line or "relevance" in line_lower:
                    try:
                        relevance_score = self._extract_score(line)
                    except:
                        pass
                elif "可靠性" in line or "reliability" in line_lower:
                    try:
                        reliability_score = self._extract_score(line)
                    except:
                        pass
                elif "置信度" in line or "confidence" in line_lower:
                    try:
                        confidence_score = self._extract_score(line)
                    except:
                        pass
            
            # 如果置信度分数没有被解析，使用相关性和可靠性的平均值
            if confidence_score == 0.5 and (relevance_score != 0.5 or reliability_score != 0.5):
                confidence_score = (relevance_score + reliability_score) / 2
        except Exception as e:
            print(f"解析分数出错: {e}")
        
        return {
            "relevance_score": relevance_score,
            "reliability_score": reliability_score,
            "confidence_score": confidence_score,
        }
    
    def _extract_score(self, text: str) -> float:
        """从文本中提取0-1之间的分数"""
        import re
        # 查找0.XX格式的数字
        matches = re.findall(r"0?\.\d+", text)
        if matches:
            score = float(matches[0])
            # 确保在0-1范围内
            return max(0.0, min(1.0, score))
        return 0.5
    
    def analyze_price_trend(self, articles: list) -> dict:
        """分析白银价格涨跌趋势"""
        if not self.client:
            return {
                "up_probability": 50.0,
                "down_probability": 50.0,
                "neutral_probability": 0.0,
                "summary": "未配置AI API，无法进行趋势分析",
                "factors": [],
                "confidence": "low",
            }
        
        try:
            # 构建文章摘要
            articles_summary = []
            for article in articles[:10]:  # 最多分析10篇文章
                title = article.title if hasattr(article, 'title') else article.get('title', '')
                ai_analysis = article.ai_analysis if hasattr(article, 'ai_analysis') else article.get('ai_analysis', '')
                if ai_analysis:
                    articles_summary.append(f"标题: {title}\n分析: {ai_analysis[:200]}")
            
            if not articles_summary:
                return {
                    "up_probability": 50.0,
                    "down_probability": 50.0,
                    "neutral_probability": 0.0,
                    "summary": "暂无足够的数据进行分析",
                    "factors": [],
                    "confidence": "low",
                }
            
            articles_text = "\n\n".join(articles_summary)
            
            # 构建分析提示
            prompt = f"""
基于以下高置信度的白银投资相关文章和分析，请评估白银价格的涨跌概率。

文章和分析摘要：
{articles_text}

请综合分析这些信息，评估白银价格在未来短期（1-2周）内的涨跌概率，并给出简要分析。

请以以下格式返回：
上涨概率: XX% (0-100的整数)
下跌概率: XX% (0-100的整数)
中性概率: XX% (0-100的整数，三个概率之和应为100)
简要分析: [200字以内的分析说明，包括主要影响因素]
关键因素: [列出2-5个主要影响因素，用逗号分隔]
分析置信度: high/medium/low

注意：
- 上涨概率：价格可能上涨的概率
- 下跌概率：价格可能下跌的概率  
- 中性概率：价格可能横盘或波动较小的概率
- 三个概率之和必须等于100%
- 简要分析应该基于文章中的信息，客观分析影响白银价格的主要因素
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
                                "content": "你是一个专业的贵金属投资分析专家，擅长分析白银价格走势和影响因素。"
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        temperature=0.5,
                        max_tokens=800,
                    )
                    
                    analysis_text = response.choices[0].message.content
                    
                    # 如果成功，更新当前使用的模型
                    if model_to_try != self.model:
                        print(f"模型 {self.model} 不可用，已切换到 {model_to_try}")
                        self.model = model_to_try
                    
                    # 解析结果
                    return self._parse_trend_analysis(analysis_text)
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
            print(f"趋势分析出错: {e}")
            error_msg = str(e)
            if "403" in error_msg or "not available" in error_msg.lower():
                error_msg = "模型在您的地区不可用，请尝试配置其他模型（通过AI_MODEL环境变量）"
            return {
                "up_probability": 50.0,
                "down_probability": 50.0,
                "neutral_probability": 0.0,
                "summary": f"分析过程出错: {error_msg}",
                "factors": [],
                "confidence": "low",
            }
    
    def _parse_trend_analysis(self, analysis_text: str) -> dict:
        """解析趋势分析结果"""
        import re
        
        # 默认值
        up_probability = 50.0
        down_probability = 50.0
        neutral_probability = 0.0
        summary = "分析结果解析失败"
        factors = []
        confidence = "medium"
        
        try:
            lines = analysis_text.split("\n")
            
            for line in lines:
                line_lower = line.lower()
                
                # 提取概率
                if "上涨概率" in line or "up" in line_lower or "上涨" in line:
                    matches = re.findall(r"\d+", line)
                    if matches:
                        up_probability = float(matches[0])
                elif "下跌概率" in line or "down" in line_lower or "下跌" in line:
                    matches = re.findall(r"\d+", line)
                    if matches:
                        down_probability = float(matches[0])
                elif "中性概率" in line or "neutral" in line_lower or "中性" in line:
                    matches = re.findall(r"\d+", line)
                    if matches:
                        neutral_probability = float(matches[0])
                
                # 提取简要分析
                if "简要分析" in line or "分析:" in line or "分析：" in line:
                    # 获取冒号后的内容
                    if ":" in line or "：" in line:
                        sep = ":" if ":" in line else "："
                        summary = line.split(sep, 1)[1].strip()
                        # 继续读取后续行直到关键因素或结束
                        idx = lines.index(line)
                        for next_line in lines[idx+1:]:
                            if "关键因素" in next_line or "factors" in next_line.lower() or "因素" in next_line:
                                break
                            if next_line.strip() and not next_line.strip().startswith("上涨") and not next_line.strip().startswith("下跌") and not next_line.strip().startswith("中性"):
                                summary += " " + next_line.strip()
                
                # 提取关键因素
                if "关键因素" in line or "factors" in line_lower or "因素:" in line or "因素：" in line:
                    if ":" in line or "：" in line:
                        sep = ":" if ":" in line else "："
                        factors_text = line.split(sep, 1)[1].strip()
                        factors = [f.strip() for f in factors_text.split(",") if f.strip()][:5]
                
                # 提取置信度
                if "置信度" in line or "confidence" in line_lower:
                    if "high" in line_lower:
                        confidence = "high"
                    elif "low" in line_lower:
                        confidence = "low"
                    else:
                        confidence = "medium"
            
            # 如果概率之和不为100，进行归一化
            total = up_probability + down_probability + neutral_probability
            if total > 0 and total != 100:
                up_probability = up_probability / total * 100
                down_probability = down_probability / total * 100
                neutral_probability = neutral_probability / total * 100
            
            # 如果没有找到简要分析，使用整个文本（去掉概率部分）
            if summary == "分析结果解析失败":
                summary_lines = []
                for line in lines:
                    if not any(keyword in line for keyword in ["上涨概率", "下跌概率", "中性概率", "关键因素", "置信度", "up", "down", "neutral"]):
                        if line.strip():
                            summary_lines.append(line.strip())
                summary = " ".join(summary_lines)[:500] or "无法解析分析内容"
            
        except Exception as e:
            print(f"解析趋势分析结果出错: {e}")
        
        return {
            "up_probability": round(up_probability, 1),
            "down_probability": round(down_probability, 1),
            "neutral_probability": round(neutral_probability, 1),
            "summary": summary,
            "factors": factors,
            "confidence": confidence,
        }