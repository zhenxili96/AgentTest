"""配置管理模块"""
import os
from dotenv import load_dotenv
from typing import List

# 加载环境变量
load_dotenv()


class Config:
    """应用配置类"""
    
    # AI API配置（支持OpenAI、OpenRouter和Bltcy）
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    BLTCY_API_KEY: str = os.getenv("BLTCY_API_KEY", "")
    # AI服务提供商选择：openai、openrouter 或 bltcy（默认优先级：bltcy > openrouter > openai）
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", 
        "bltcy" if os.getenv("BLTCY_API_KEY") 
        else ("openrouter" if os.getenv("OPENROUTER_API_KEY") else "openai"))
    # AI模型配置（可通过环境变量覆盖）
    AI_MODEL: str = os.getenv("AI_MODEL", "")  # 如果为空，将使用默认模型或备用模型
    
    # NewsAPI配置
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")
    
    # Alpha Vantage配置（可选）
    ALPHA_VANTAGE_API_KEY: str = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    
    # Finnhub配置（新闻+行情，免费60次/分钟）
    FINNHUB_API_KEY: str = os.getenv("FINNHUB_API_KEY", "")
    
    # GNews API配置（新闻搜索，免费100次/天）
    GNEWS_API_KEY: str = os.getenv("GNEWS_API_KEY", "")
    
    # Marketaux API配置（金融新闻，免费100次/天）
    MARKETAUX_API_KEY: str = os.getenv("MARKETAUX_API_KEY", "")
    
    # FRED API配置（美联储经济数据）
    FRED_API_KEY: str = os.getenv("FRED_API_KEY", "")
    
    # Tushare配置（中国市场数据）
    TUSHARE_TOKEN: str = os.getenv("TUSHARE_TOKEN", "")

    # 默认关注的股市代码（可通过环境变量覆盖）
    STOCK_SYMBOLS: List[str] = [
        symbol.strip().upper()
        for symbol in os.getenv(
            "STOCK_SYMBOLS",
            "SPY,QQQ,DIA"
        ).split(",")
        if symbol.strip()
    ]
    
    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///silver_investment.db")

    # 默认投资主题（可通过环境变量覆盖）
    DEFAULT_THEME: str = os.getenv("DEFAULT_THEME", "白银")
    
    # 搜索配置
    SEARCH_INTERVAL_MINUTES: int = int(os.getenv("SEARCH_INTERVAL_MINUTES", "30"))
    MAX_ARTICLES_PER_SEARCH: int = int(os.getenv("MAX_ARTICLES_PER_SEARCH", "50"))
    MIN_CONFIDENCE_SCORE: float = float(os.getenv("MIN_CONFIDENCE_SCORE", "0.7"))
    KEYWORD_MINING_INTERVAL_HOURS: int = int(os.getenv("KEYWORD_MINING_INTERVAL_HOURS", "4"))
    RECOMMENDATION_INTERVAL_MINUTES: int = int(os.getenv("RECOMMENDATION_INTERVAL_MINUTES", "120"))

    # 多Agent配置
    AGENT_MAX_ARTICLES: int = int(os.getenv("AGENT_MAX_ARTICLES", "40"))
    AGENT_MIN_SOURCES: int = int(os.getenv("AGENT_MIN_SOURCES", "4"))
    AGENT_TOP_EVIDENCE_COUNT: int = int(os.getenv("AGENT_TOP_EVIDENCE_COUNT", "8"))
    AGENT_MAX_STOCKS: int = int(os.getenv("AGENT_MAX_STOCKS", "8"))
    
    # 搜索关键词（白银期货投资相关，包括上下游和关联因素）
    # 核心关键词：白银、银价、白银期货
    # 上游：矿业、矿产、开采、供应
    # 下游：工业应用、电子产品、太阳能、医疗、珠宝
    # 宏观经济：通胀、货币政策、美元、利率、经济数据
    # 市场因素：期货、COMEX、持仓、库存、价格走势
    # 相关商品：黄金、贵金属、铜等工业金属
    SEARCH_KEYWORDS: List[str] = [
        kw.strip() for kw in os.getenv(
            "SEARCH_KEYWORDS", 
            "白银,silver,银价,白银期货,precious metals,贵金属,"
            "mining,矿业,矿产,mineral,commodities,商品,"
            "industrial demand,工业需求,electronics,电子产品,solar,太阳能,"
            "inflation,通胀,monetary policy,货币政策,Fed,美联储,"
            "dollar,美元,interest rate,利率,economic data,经济数据,"
            "futures,期货,COMEX,持仓,inventory,库存,"
            "gold,黄金,copper,铜,industrial metals,工业金属,"
            "supply chain,供应链,demand,需求,price,价格"
        ).split(",") if kw.strip()
    ]
    
    # 财经RSS源（支持中英文，NewsAPI不可用时仍可使用）
    # 注意：某些RSS源可能无法访问，程序会自动跳过
    RSS_FEEDS: List[str] = [
        # 英文财经源
        "https://finance.yahoo.com/rss/headline",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://feeds.reuters.com/reuters/businessNews",
        "https://feeds.bloomberg.com/markets/news.rss",
        # 通用财经RSS
        "http://feeds.feedburner.com/FinancialTimes/com/companies",
        
        # 贵金属专业网站
        "https://www.kitco.com/rss/gold.xml",                    # Kitco黄金白银
        "https://www.kitco.com/rss/all_kitco_news.xml",          # Kitco全部新闻
        "https://www.investing.com/rss/news_14.rss",             # Investing.com商品
        "https://www.investing.com/rss/news_25.rss",             # Investing.com经济指标
        
        # 宏观经济/市场分析
        "https://seekingalpha.com/market_currents.xml",          # Seeking Alpha市场动态
        "https://seekingalpha.com/tag/etfs.xml",                 # Seeking Alpha ETF
        "https://www.marketwatch.com/rss/topstories",            # MarketWatch头条
        "https://www.marketwatch.com/rss/marketpulse",           # MarketWatch市场脉搏
        
        # 中文源（通过RSSHub，需要可用的RSSHub实例）
        # "https://rsshub.app/cls/depth/1000",                   # 财联社深度
        # "https://rsshub.app/eastmoney/important",              # 东方财富要闻
        # "https://rsshub.app/sina/finance",                     # 新浪财经
    ]
    
    # 用户代理（用于爬虫）
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    @classmethod
    def validate(cls) -> bool:
        """验证必要的配置是否已设置"""
        # AI API是可选的（Bltcy、OpenRouter或OpenAI，如果没有配置，会使用默认置信度评估）
        # NewsAPI是可选的（可以使用RSS源替代）
        has_ai_api = cls.BLTCY_API_KEY or cls.OPENROUTER_API_KEY or cls.OPENAI_API_KEY
        warnings = []
        optional_info = []
        
        if not has_ai_api:
            warnings.append("AI API（BLTCY_API_KEY、OPENROUTER_API_KEY或OPENAI_API_KEY未配置，将使用默认置信度评估，所有文章分数为0.5）")
        
        if not cls.NEWS_API_KEY:
            warnings.append("NEWS_API_KEY（未配置将仅使用RSS源）")
        
        # 新增数据源状态
        if cls.FINNHUB_API_KEY:
            optional_info.append("✅ Finnhub（新闻+行情）")
        else:
            optional_info.append("⬜ FINNHUB_API_KEY（未配置，跳过Finnhub数据源）")
        
        if cls.GNEWS_API_KEY:
            optional_info.append("✅ GNews（新闻搜索）")
        else:
            optional_info.append("⬜ GNEWS_API_KEY（未配置，跳过GNews数据源）")
        
        if cls.MARKETAUX_API_KEY:
            optional_info.append("✅ Marketaux（金融新闻）")
        else:
            optional_info.append("⬜ MARKETAUX_API_KEY（未配置，跳过Marketaux数据源）")
        
        if cls.FRED_API_KEY:
            optional_info.append("✅ FRED（宏观经济数据）")
        else:
            optional_info.append("⬜ FRED_API_KEY（未配置，跳过FRED数据源）")
        
        if cls.TUSHARE_TOKEN:
            optional_info.append("✅ Tushare（中国市场数据）")
        else:
            optional_info.append("⬜ TUSHARE_TOKEN（未配置，跳过Tushare数据源）")
        
        if warnings:
            print(f"提示：可选配置项未设置:")
            for warning in warnings:
                print(f"  - {warning}")
        
        if optional_info:
            print(f"\n数据源状态:")
            for info in optional_info:
                print(f"  {info}")
        
        return True
