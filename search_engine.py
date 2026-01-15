"""信息搜索引擎模块"""
import requests
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional, Union
from config import Config


class SearchEngine:
    """搜索引擎类，整合多个数据源"""
    
    def __init__(self):
        self.news_api_key = Config.NEWS_API_KEY
        self.user_agent = Config.USER_AGENT
        self.keywords = Config.SEARCH_KEYWORDS

    def _normalize_keywords(
        self,
        theme: Optional[str] = None,
        keywords: Optional[Union[List[str], str]] = None
    ) -> List[str]:
        """根据主题或外部关键词生成搜索关键词列表"""
        normalized: List[str] = []

        if isinstance(keywords, str):
            split_keywords = [kw.strip() for kw in keywords.split(",") if kw.strip()]
            normalized.extend(split_keywords)
        elif isinstance(keywords, list):
            normalized.extend([kw.strip() for kw in keywords if isinstance(kw, str) and kw.strip()])

        if theme:
            theme = theme.strip()
            if theme:
                normalized.append(theme)
                theme_parts = [
                    part.strip()
                    for part in theme.replace("，", ",").replace("、", ",").split(",")
                    if part.strip()
                ]
                normalized.extend(theme_parts)

        if not normalized:
            normalized = list(self.keywords)

        # 去重保持顺序
        seen = set()
        deduped = []
        for kw in normalized:
            if kw not in seen:
                seen.add(kw)
                deduped.append(kw)
        return deduped

    def _normalize_symbols(
        self,
        symbols: Optional[Union[List[str], str]] = None
    ) -> List[str]:
        """标准化股票代码列表"""
        normalized: List[str] = []

        if isinstance(symbols, str):
            normalized.extend([
                symbol.strip().upper()
                for symbol in symbols.replace("，", ",").split(",")
                if symbol.strip()
            ])
        elif isinstance(symbols, list):
            normalized.extend([
                str(symbol).strip().upper()
                for symbol in symbols
                if str(symbol).strip()
            ])

        if not normalized:
            normalized = list(Config.STOCK_SYMBOLS)

        seen = set()
        deduped = []
        for symbol in normalized:
            if symbol not in seen:
                seen.add(symbol)
                deduped.append(symbol)
        return deduped
    
    def search_newsapi(
        self,
        query: str,
        max_results: int = 50,
        theme: Optional[str] = None,
        keywords: Optional[Union[List[str], str]] = None
    ) -> List[Dict]:
        """使用NewsAPI搜索新闻"""
        if not self.news_api_key:
            return []

        active_keywords = self._normalize_keywords(theme=theme, keywords=keywords)
        articles = []
        try:
            # 构建查询（包含多个关键词）
            search_query = " OR ".join([f'"{kw}"' for kw in active_keywords])
            
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": search_query,
                "language": "zh,en",
                "sortBy": "publishedAt",
                "pageSize": min(max_results, 100),
                "apiKey": self.news_api_key,
            }
            
            headers = {"User-Agent": self.user_agent}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get("status") == "ok":
                for item in data.get("articles", [])[:max_results]:
                    # 解析发布日期
                    published_at = self._parse_date(item.get("publishedAt"))
                    
                    articles.append({
                        "title": item.get("title", ""),
                        "content": item.get("description", "") + " " + item.get("content", ""),
                        "url": item.get("url", ""),
                        "source": item.get("source", {}).get("name", "NewsAPI"),
                        "author": item.get("author"),
                        "published_at": published_at,
                        "keywords": ", ".join(
                            [
                                kw
                                for kw in active_keywords
                                if kw.lower() in item.get("title", "").lower()
                                or kw.lower() in item.get("description", "").lower()
                            ]
                        ),
                    })
        except Exception as e:
            print(f"NewsAPI搜索出错: {e}")
        
        return articles
    
    def search_rss_feeds(
        self,
        max_results: int = 50,
        theme: Optional[str] = None,
        keywords: Optional[Union[List[str], str]] = None
    ) -> List[Dict]:
        """搜索RSS源"""
        active_keywords = self._normalize_keywords(theme=theme, keywords=keywords)
        articles = []
        successful_feeds = 0
        total_feed_articles = 0
        
        for feed_url in Config.RSS_FEEDS:
            try:
                # 设置超时和headers
                feed = feedparser.parse(feed_url)
                
                # 检查feed是否有效
                if not hasattr(feed, 'entries') or len(feed.entries) == 0:
                    print(f"  ⚠️ RSS源无文章: {feed_url.split('/')[2] if '/' in feed_url else feed_url}")
                    continue
                
                successful_feeds += 1
                feed_articles_count = len(feed.entries)
                total_feed_articles += feed_articles_count
                articles_per_feed = max(5, max_results // max(len(Config.RSS_FEEDS), 1))
                matched_count = 0
                
                for entry in feed.entries[:articles_per_feed]:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "") or entry.get("description", "")
                    
                    if not title:
                        continue
                    
                    # 检查是否包含关键词
                    title_lower = title.lower()
                    summary_lower = summary.lower()
                    
                    matched_keywords = [
                        kw for kw in active_keywords 
                        if kw and (kw.lower() in title_lower or kw.lower() in summary_lower)
                    ]
                    
                    if not matched_keywords:
                        continue
                    
                    matched_count += 1
                    # 解析发布日期
                    published_at = self._parse_date(entry.get("published") or entry.get("updated"))
                    
                    articles.append({
                        "title": title,
                        "content": summary,
                        "url": entry.get("link", ""),
                        "source": feed.feed.get("title", "") or feed_url.split("/")[2],
                        "author": entry.get("author"),
                        "published_at": published_at,
                        "keywords": ", ".join(matched_keywords),
                    })
                
                if matched_count > 0:
                    print(f"  ✅ {feed_url.split('/')[2] if '/' in feed_url else feed_url}: 找到 {matched_count} 篇匹配文章（共 {feed_articles_count} 篇）")
                
            except Exception as e:
                # 显示错误信息以便调试
                print(f"  ❌ RSS源访问失败: {feed_url.split('/')[2] if '/' in feed_url else feed_url} - {str(e)[:50]}")
                continue
        
        if successful_feeds == 0:
            print("⚠️ 警告：所有RSS源都无法访问，请检查网络连接或RSS源地址")
        elif len(articles) == 0 and total_feed_articles > 0:
            print(f"⚠️ 提示：成功访问 {successful_feeds} 个RSS源（共 {total_feed_articles} 篇文章），但没有文章匹配关键词")
            print(f"   关键词: {', '.join(active_keywords)}")
            print(f"   建议: 尝试更通用的关键词，或检查RSS源是否包含相关主题的文章")
        
        return articles
    
    def search_all(
        self,
        max_results: int = 50,
        theme: Optional[str] = None,
        keywords: Optional[Union[List[str], str]] = None
    ) -> List[Dict]:
        """搜索所有数据源"""
        all_articles = []
        
        # 从NewsAPI搜索
        newsapi_articles = self.search_newsapi("", max_results, theme=theme, keywords=keywords)
        all_articles.extend(newsapi_articles)
        
        # 从RSS源搜索
        rss_articles = self.search_rss_feeds(max_results, theme=theme, keywords=keywords)
        all_articles.extend(rss_articles)
        
        # 去重（基于URL）
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            url = article.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(article)
        
        return unique_articles[:max_results]

    def fetch_stock_market_info(
        self,
        symbols: Optional[Union[List[str], str]] = None
    ) -> Dict:
        """获取股市行情信息（基于Alpha Vantage）"""
        if not Config.ALPHA_VANTAGE_API_KEY:
            return {
                "success": False,
                "error": "ALPHA_VANTAGE_API_KEY 未配置",
                "quotes": [],
                "requested_symbols": self._normalize_symbols(symbols),
            }

        active_symbols = self._normalize_symbols(symbols)
        quotes = []
        errors = []

        for symbol in active_symbols:
            try:
                url = "https://www.alphavantage.co/query"
                params = {
                    "function": "GLOBAL_QUOTE",
                    "symbol": symbol,
                    "apikey": Config.ALPHA_VANTAGE_API_KEY,
                }
                headers = {"User-Agent": self.user_agent}
                response = requests.get(url, params=params, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()

                if "Note" in data:
                    errors.append({"symbol": symbol, "error": data.get("Note")})
                    continue

                quote = data.get("Global Quote", {}) or {}
                if not quote:
                    errors.append({"symbol": symbol, "error": "未返回有效行情数据"})
                    continue

                quotes.append({
                    "symbol": quote.get("01. symbol", symbol),
                    "price": self._safe_float(quote.get("05. price")),
                    "change": self._safe_float(quote.get("09. change")),
                    "change_percent": quote.get("10. change percent", ""),
                    "latest_trading_day": quote.get("07. latest trading day", ""),
                    "source": "Alpha Vantage",
                })
            except Exception as e:
                errors.append({"symbol": symbol, "error": str(e)})

        return {
            "success": len(quotes) > 0,
            "quotes": quotes,
            "errors": errors,
            "requested_symbols": active_symbols,
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }

    def build_stock_market_context(self, stock_data: Dict) -> str:
        """将股市行情转换为分析上下文文本"""
        if not stock_data or not stock_data.get("quotes"):
            return ""

        lines = ["股市行情快照（Alpha Vantage）："]
        for quote in stock_data.get("quotes", []):
            symbol = quote.get("symbol", "")
            price = quote.get("price")
            change = quote.get("change")
            change_percent = quote.get("change_percent", "")
            latest_day = quote.get("latest_trading_day", "")
            price_text = f"{price}" if price is not None else "N/A"
            change_text = f"{change}" if change is not None else "N/A"
            lines.append(
                f"- {symbol}: {price_text} ({change_text} / {change_percent}) "
                f"最新交易日: {latest_day}"
            )

        if stock_data.get("errors"):
            lines.append("注意：部分行情获取失败，可能因频率限制或代码无效。")

        return "\n".join(lines)
    
    def _parse_date(self, date_str: Optional[str]) -> datetime:
        """解析日期字符串"""
        if not date_str:
            return datetime.utcnow()
        
        # 尝试多种日期格式
        formats = [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%a, %d %b %Y %H:%M:%S %Z",
            "%a, %d %b %Y %H:%M:%S %z",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # 如果都失败了，返回当前时间
        return datetime.utcnow()

    @staticmethod
    def _safe_float(value: Optional[str]) -> Optional[float]:
        """安全解析浮点数"""
        try:
            return float(value) if value not in (None, "") else None
        except (TypeError, ValueError):
            return None
