"""配置管理模块"""
import os
from dotenv import load_dotenv
from typing import List

# 加载环境变量
load_dotenv()


class Config:
    """应用配置类"""
    
    # AI API配置（支持OpenAI和OpenRouter）
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    # AI服务提供商选择：openai 或 openrouter（默认优先使用OpenRouter如果配置了）
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "openrouter" if os.getenv("OPENROUTER_API_KEY") else "openai")
    # AI模型配置（可通过环境变量覆盖）
    AI_MODEL: str = os.getenv("AI_MODEL", "")  # 如果为空，将使用默认模型或备用模型
    
    # NewsAPI配置
    NEWS_API_KEY: str = os.getenv("NEWS_API_KEY", "")
    
    # Alpha Vantage配置（可选）
    ALPHA_VANTAGE_API_KEY: str = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    
    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///silver_investment.db")
    
    # 搜索配置
    SEARCH_INTERVAL_MINUTES: int = int(os.getenv("SEARCH_INTERVAL_MINUTES", "30"))
    MAX_ARTICLES_PER_SEARCH: int = int(os.getenv("MAX_ARTICLES_PER_SEARCH", "50"))
    MIN_CONFIDENCE_SCORE: float = float(os.getenv("MIN_CONFIDENCE_SCORE", "0.7"))
    
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
        # 注意：中文RSS源格式可能不同，需要特殊处理
        # 如需添加中文源，建议使用专门的RSS聚合服务
    ]
    
    # 用户代理（用于爬虫）
    USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    
    @classmethod
    def validate(cls) -> bool:
        """验证必要的配置是否已设置"""
        # AI API是可选的（OpenRouter或OpenAI，如果没有配置，会使用默认置信度评估）
        # NewsAPI是可选的（可以使用RSS源替代）
        has_ai_api = cls.OPENROUTER_API_KEY or cls.OPENAI_API_KEY
        warnings = []
        
        if not has_ai_api:
            warnings.append("AI API（OPENROUTER_API_KEY或OPENAI_API_KEY未配置，将使用默认置信度评估，所有文章分数为0.5）")
        
        if not cls.NEWS_API_KEY:
            warnings.append("NEWS_API_KEY（未配置将仅使用RSS源）")
        
        if warnings:
            print(f"提示：可选配置项未设置:")
            for warning in warnings:
                print(f"  - {warning}")
        
        return True
