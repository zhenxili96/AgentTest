"""股票识别模块 - 从关键词和文章中识别相关股票"""
from openai import OpenAI
from typing import List, Dict, Set, Optional, Any
from datetime import datetime
import re
from config import Config
from database import db


class StockIdentifier:
    """股票识别类 - 使用AI从关键词和文章中识别相关股票"""
    
    def __init__(self):
        # 初始化AI客户端（与KeywordMiner类似的逻辑）
        self.provider = Config.AI_PROVIDER
        self.api_key = None
        self.base_url = None
        self.model = "gpt-4o-mini"
        self.client = None
        
        if self.provider == "bltcy" and Config.BLTCY_API_KEY:
            self.api_key = Config.BLTCY_API_KEY
            self.base_url = "https://api.bltcy.ai/v1"
            self.fallback_models = [
                "gpt-4o-mini",
                "gpt-3.5-turbo",
                "gpt-4-mini",
                "claude-3-haiku",
            ]
            if Config.AI_MODEL:
                self.model = Config.AI_MODEL
            else:
                self.model = self.fallback_models[0]
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        elif self.provider == "openrouter" and Config.OPENROUTER_API_KEY:
            self.api_key = Config.OPENROUTER_API_KEY
            self.base_url = "https://openrouter.ai/api/v1"
            self.fallback_models = [
                "openai/gpt-4o-mini",
                "openai/gpt-3.5-turbo",
                "anthropic/claude-3-haiku",
                "google/gemini-pro",
            ]
            if Config.AI_MODEL:
                self.model = Config.AI_MODEL
            else:
                self.model = self.fallback_models[0]
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        elif Config.OPENAI_API_KEY:
            self.api_key = Config.OPENAI_API_KEY
            self.base_url = None
            self.fallback_models = [
                "gpt-4o-mini",
                "gpt-3.5-turbo",
                "gpt-4-mini",
            ]
            if Config.AI_MODEL:
                self.model = Config.AI_MODEL
            else:
                self.model = self.fallback_models[0]
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.fallback_models = []
        
        # 常见股票代码模式（用于辅助识别）
        self.stock_pattern = re.compile(r'\b[A-Z]{1,5}\b')
    
    def identify_stocks_from_keywords(
        self,
        keywords: List[str],
        theme: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """从关键词列表中识别相关股票"""
        if not self.client:
            print("⚠️ 未配置AI API，无法进行股票识别")
            return []
        
        if not keywords:
            return []
        
        try:
            theme_name = theme or Config.DEFAULT_THEME
            keywords_text = "\n".join([f"- {kw}" for kw in keywords[:50]])  # 限制前50个关键词
            
            prompt = f"""请从以下与{theme_name}投资相关的关键词中，识别出可能相关的股票、A股和期货代码。

关键词列表：
{keywords_text}

任务要求：
1. 识别出与这些关键词相关的：
   - 美股代码（1-5个字母，如AAPL、SLV等）
   - A股代码（6位数字，如000001、600519等，需要标注市场：SSE上交所或SZSE深交所）
   - 期货代码（如AG、AU、CU等，需要标注交易所：SHFE上期所、DCE大商所、CZCE郑商所、CFFEX中金所）
2. 包括但不限于：矿业公司、贵金属ETF、工业金属相关股票、能源相关股票、期货合约等
3. 每个标的需要说明其与{theme_name}投资的相关性
4. 只返回真实存在的代码，不要返回占位符或示例代码

请以以下格式返回，每个标的一行：
代码 | 类型(us_stock/a_stock/futures) | 市场/交易所 | 名称 | 相关性说明

示例（真实标的）：
SLV | us_stock | NYSE | iShares Silver Trust | 白银ETF，直接跟踪白银价格
000001 | a_stock | SZSE | 平安银行 | 银行股，与贵金属投资相关
AG | futures | SHFE | 白银期货 | 上海期货交易所白银期货主力合约
"""
            
            # 尝试调用AI API
            models_to_try = [self.model] + [m for m in self.fallback_models if m != self.model]
            last_error = None
            
            for model_to_try in models_to_try:
                try:
                    response = self.client.chat.completions.create(
                        model=model_to_try,
                        messages=[
                            {
                                "role": "system",
                                "content": f"你是一个专业的股票市场分析师，擅长识别与{theme_name}投资相关的股票代码。"
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        temperature=0.3,
                        max_tokens=1000,
                    )
                    
                    result_text = response.choices[0].message.content
                    
                    if model_to_try != self.model:
                        print(f"模型 {self.model} 不可用，已切换到 {model_to_try}")
                        self.model = model_to_try
                    
                    # 解析股票代码
                    stocks = self._parse_stocks_from_text(result_text, theme_name)
                    
                    print(f"✅ 从关键词中识别出 {len(stocks)} 只相关股票")
                    return stocks
                except Exception as e:
                    last_error = e
                    error_str = str(e)
                    if "403" in error_str or "not available" in error_str.lower() or "region" in error_str.lower():
                        print(f"模型 {model_to_try} 在您的地区不可用，尝试下一个模型...")
                        continue
                    raise
            
            raise last_error if last_error else Exception("所有模型都不可用")
            
        except Exception as e:
            print(f"❌ 股票识别出错: {e}")
            return []
    
    def identify_stocks_from_articles(
        self,
        articles: List,
        theme: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """从高置信度文章中识别相关股票"""
        if not self.client:
            print("⚠️ 未配置AI API，无法进行股票识别")
            return []
        
        if not articles:
            return []
        
        try:
            theme_name = theme or Config.DEFAULT_THEME
            articles_text = self._build_articles_summary(articles[:limit], theme_name)
            
            prompt = f"""请从以下高置信度的{theme_name}投资相关文章中，识别出可能相关的股票、A股和期货代码。

{articles_text}

任务要求：
1. 识别出文章中提到的或与文章主题相关的：
   - 美股代码（1-5个字母，如AAPL、SLV等）
   - A股代码（6位数字，如000001、600519等，需要标注市场：SSE上交所或SZSE深交所）
   - 期货代码（如AG、AU、CU等，需要标注交易所：SHFE上期所、DCE大商所、CZCE郑商所、CFFEX中金所）
2. 包括但不限于：矿业公司、贵金属ETF、工业金属相关股票、能源相关股票、期货合约等
3. 每个标的需要说明其与{theme_name}投资的相关性
4. 只返回真实存在的代码，不要返回占位符或示例代码

请以以下格式返回，每个标的一行：
代码 | 类型(us_stock/a_stock/futures) | 市场/交易所 | 名称 | 相关性说明
"""
            
            # 尝试调用AI API
            models_to_try = [self.model] + [m for m in self.fallback_models if m != self.model]
            last_error = None
            
            for model_to_try in models_to_try:
                try:
                    response = self.client.chat.completions.create(
                        model=model_to_try,
                        messages=[
                            {
                                "role": "system",
                                "content": f"你是一个专业的股票市场分析师，擅长从新闻文章中识别与{theme_name}投资相关的股票代码。"
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        temperature=0.3,
                        max_tokens=1000,
                    )
                    
                    result_text = response.choices[0].message.content
                    
                    if model_to_try != self.model:
                        print(f"模型 {self.model} 不可用，已切换到 {model_to_try}")
                        self.model = model_to_try
                    
                    # 解析股票代码
                    stocks = self._parse_stocks_from_text(result_text, theme_name)
                    
                    print(f"✅ 从文章中识别出 {len(stocks)} 只相关股票")
                    return stocks
                except Exception as e:
                    last_error = e
                    error_str = str(e)
                    if "403" in error_str or "not available" in error_str.lower() or "region" in error_str.lower():
                        print(f"模型 {model_to_try} 在您的地区不可用，尝试下一个模型...")
                        continue
                    raise
            
            raise last_error if last_error else Exception("所有模型都不可用")
            
        except Exception as e:
            print(f"❌ 股票识别出错: {e}")
            return []
    
    def _build_articles_summary(self, articles, theme: str) -> str:
        """构建文章摘要文本用于AI分析"""
        summary_parts = []
        summary_parts.append(f"以下是 {len(articles)} 篇高置信度的{theme}投资相关文章：\n")
        
        for i, article in enumerate(articles, 1):
            summary_parts.append(f"\n文章 {i}:")
            summary_parts.append(f"标题: {article.title if hasattr(article, 'title') else article.get('title', '')}")
            if hasattr(article, 'content') and article.content:
                content_preview = article.content[:300]
                summary_parts.append(f"内容摘要: {content_preview}")
            elif article.get('content'):
                content_preview = article['content'][:300]
                summary_parts.append(f"内容摘要: {content_preview}")
        
        return "\n".join(summary_parts)
    
    def _parse_stocks_from_text(self, text: str, theme: str) -> List[Dict[str, Any]]:
        """从AI返回的文本中解析股票代码"""
        stocks = []
        seen_symbols = set()
        lines = text.split("\n")
        
        for line in lines:
            line = line.strip()
            if not line or "|" not in line:
                continue
            
            try:
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 2:
                    symbol = parts[0].strip().upper()
                    if not symbol:
                        continue
                    
                    # 根据类型验证代码格式
                    stock_type = "us_stock"  # 默认
                    market = None
                    
                    if len(parts) >= 3:
                        type_str = parts[1].strip().lower()
                        if "a_stock" in type_str or "a股" in type_str:
                            stock_type = "a_stock"
                            # A股代码应该是6位数字
                            if not (symbol.isdigit() and len(symbol) == 6):
                                continue
                        elif "futures" in type_str or "期货" in type_str:
                            stock_type = "futures"
                        elif "us_stock" in type_str or "美股" in type_str:
                            stock_type = "us_stock"
                            # 美股代码1-5个字母
                            if len(symbol) > 5 or not symbol.isalpha():
                                continue
                        else:
                            # 尝试自动判断类型
                            if symbol.isdigit() and len(symbol) == 6:
                                stock_type = "a_stock"
                            elif len(symbol) <= 5 and symbol.isalpha():
                                stock_type = "us_stock"
                            else:
                                stock_type = "futures"
                    
                    # 获取市场/交易所信息
                    if len(parts) >= 3:
                        market = parts[2].strip() if len(parts) > 2 else None
                    
                    # 过滤掉明显的占位符
                    if self._is_invalid_symbol(symbol):
                        continue
                    
                    # 去重（使用symbol+stock_type作为唯一键）
                    unique_key = f"{symbol}_{stock_type}"
                    if unique_key in seen_symbols:
                        continue
                    seen_symbols.add(unique_key)
                    
                    company_name = parts[3] if len(parts) > 3 else (parts[1] if len(parts) > 1 else "")
                    relevance = parts[4] if len(parts) > 4 else (parts[2] if len(parts) > 2 else "")
                    
                    stocks.append({
                        "symbol": symbol,
                        "stock_type": stock_type,
                        "market": market,
                        "company_name": company_name,
                        "relevance": relevance,
                        "theme": theme,
                        "identified_at": datetime.utcnow(),
                        "source": "ai_analysis"
                    })
            except Exception as e:
                continue
        
        return stocks
    
    def _is_invalid_symbol(self, symbol: str) -> bool:
        """检查股票代码是否是无效的占位符"""
        if not symbol:
            return True
        
        symbol_upper = symbol.upper()
        
        # 检查是否是占位符模式
        invalid_patterns = [
            "EXAMPLE", "TEST", "DEMO", "SAMPLE",
            "STOCK1", "STOCK2", "STOCK3",
            "SYMBOL1", "SYMBOL2", "SYMBOL3",
            "XXX", "YYY", "ZZZ", "AAA", "BBB"
        ]
        
        if symbol_upper in invalid_patterns:
            return True
        
        # 对于数字代码（A股），检查是否是明显的占位符
        if symbol.isdigit():
            if symbol in ["000000", "111111", "999999", "123456", "654321"]:
                return True
        
        # 检查是否只包含常见单词（仅对字母代码）
        if symbol.isalpha():
            common_words = ["THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "CAN", "HER", "WAS", "ONE", "OUR", "OUT", "DAY", "GET", "HAS", "HIM", "HIS", "HOW", "ITS", "MAY", "NEW", "NOW", "OLD", "SEE", "TWO", "WAY", "WHO", "BOY", "DID", "ITS", "LET", "PUT", "SAY", "SHE", "TOO", "USE"]
            if symbol_upper in common_words:
                return True
        
        return False
