"""Flask API服务"""
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from datetime import datetime, timedelta, timezone
from database import db
from search_engine import SearchEngine
from confidence_evaluator import ConfidenceEvaluator
from keyword_miner import KeywordMiner
from stock_identifier import StockIdentifier
from stock_fetcher import StockFetcher
from scheduler import Scheduler
from multi_agent import MultiAgentOrchestrator
from config import Config

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# 北京时间时区（UTC+8）
BEIJING_TZ = timezone(timedelta(hours=8))


def to_beijing_time(dt):
    """将datetime对象转换为北京时间（UTC+8）"""
    if dt is None:
        return None
    # 如果datetime没有时区信息，假设它是UTC时间
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    # 转换为北京时间
    return dt.astimezone(BEIJING_TZ)


def beijing_now():
    """获取当前北京时间"""
    return datetime.now(BEIJING_TZ)


def format_beijing_time(dt):
    """格式化时间为北京时间的ISO格式字符串"""
    if dt is None:
        return None
    beijing_dt = to_beijing_time(dt)
    return beijing_dt.isoformat()

search_engine = SearchEngine()
evaluator = ConfidenceEvaluator()
keyword_miner = KeywordMiner()
stock_identifier = StockIdentifier()
stock_fetcher = StockFetcher()
multi_agent = MultiAgentOrchestrator()

# 初始化调度器（用于后台持续获取信息）
scheduler = Scheduler()


@app.route("/")
def index():
    """主页"""
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def health():
    """健康检查"""
    return jsonify({"status": "ok", "timestamp": format_beijing_time(beijing_now())})


@app.route("/api/scheduler/status", methods=["GET"])
def scheduler_status():
    """获取后台调度任务状态"""
    try:
        status = scheduler.get_status()
        return jsonify({"success": True, "scheduler": status})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/articles", methods=["GET"])
def get_articles():
    """获取文章列表"""
    try:
        # 获取查询参数
        high_confidence_only = request.args.get("high_confidence", "false").lower() == "true"
        min_score = request.args.get("min_score", type=float)
        limit = request.args.get("limit", type=int, default=50)
        
        if high_confidence_only:
            articles = db.get_high_confidence_articles(limit=limit, min_score=min_score)
        else:
            hours = request.args.get("hours", type=int, default=24)
            articles = db.get_recent_articles(hours=hours, limit=limit)
        
        # 转换为字典
        articles_data = []
        for article in articles:
            articles_data.append({
                "id": article.id,
                "title": article.title,
                "content": article.content,
                "url": article.url,
                "source": article.source,
                "author": article.author,
                "published_at": format_beijing_time(article.published_at),
                "confidence_score": article.confidence_score,
                "relevance_score": article.relevance_score,
                "reliability_score": article.reliability_score,
                "ai_analysis": article.ai_analysis,
                "keywords": article.keywords,
                "is_high_confidence": article.is_high_confidence,
                "created_at": format_beijing_time(article.created_at),
            })
        
        return jsonify({
            "success": True,
            "count": len(articles_data),
            "articles": articles_data,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """获取统计信息"""
    try:
        stats = db.get_article_stats()
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/config", methods=["GET"])
def get_config():
    """获取系统配置信息"""
    try:
        # 获取AI配置信息
        ai_provider = getattr(evaluator, 'provider', 'unknown')
        ai_model = getattr(evaluator, 'model', '未配置')
        ai_base_url = getattr(evaluator, 'base_url', None)
        ai_configured = evaluator.client is not None
        
        # 确定API来源显示名称
        if ai_provider == "bltcy":
            api_source = "Bltcy（柏拉图AI）"
        elif ai_provider == "openrouter":
            api_source = "OpenRouter"
        elif ai_provider == "openai":
            api_source = "OpenAI"
        else:
            api_source = "未配置"
        
        # 如果未配置，显示更友好的信息
        if not ai_configured:
            api_source = "未配置"
            ai_model = "无"
        
        return jsonify({
            "success": True,
            "config": {
                "search_interval_minutes": Config.SEARCH_INTERVAL_MINUTES,
                "max_articles_per_search": Config.MAX_ARTICLES_PER_SEARCH,
                "min_confidence_score": Config.MIN_CONFIDENCE_SCORE,
            },
            "ai_config": {
                "provider": ai_provider,
                "api_source": api_source,
                "model": ai_model,
                "base_url": ai_base_url,
                "configured": ai_configured,
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/search", methods=["POST"])
def manual_search():
    """手动触发搜索"""
    try:
        data = request.get_json() or {}
        theme = data.get("theme")
        keywords = data.get("keywords")

        # 搜索文章
        articles = search_engine.search_all(
            Config.MAX_ARTICLES_PER_SEARCH,
            theme=theme,
            keywords=keywords
        )
        
        # 过滤已存在的文章，避免重复评估
        urls = [article.get("url") for article in articles if article.get("url")]
        existing_urls = db.get_existing_article_urls(urls)
        new_articles = [
            article for article in articles
            if article.get("url") not in existing_urls
        ]

        # 评估并保存
        saved_count = 0
        for article in new_articles:
            evaluation = evaluator.evaluate(article, theme=theme)
            article_data = {**article, **evaluation}
            if db.add_article(article_data):
                saved_count += 1
        
        return jsonify({
            "success": True,
            "found": len(articles),
            "new": len(new_articles),
            "skipped": len(articles) - len(new_articles),
            "saved": saved_count,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analysis/recommendation", methods=["POST"])
def generate_recommendation():
    """多Agent投资建议"""
    try:
        data = request.get_json() or {}
        theme = data.get("theme") or Config.DEFAULT_THEME
        keywords = data.get("keywords")
        risk_profile = data.get("risk_profile", "balanced")
        horizon_days = data.get("horizon_days", 30)
        max_articles = data.get("max_articles")

        result = multi_agent.run(
            theme=theme,
            keywords=keywords,
            risk_profile=risk_profile,
            horizon_days=horizon_days,
            max_articles=max_articles,
        )

        db.add_recommendation({
            "theme": result["context"]["theme"],
            "keywords": ",".join(result["context"].get("keywords") or []),
            "risk_profile": result["context"]["risk_profile"],
            "horizon_days": result["context"]["horizon_days"],
            "max_articles": result["context"]["max_articles"],
            "payload": result,
        })

        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analysis/recommendation/latest", methods=["GET"])
def get_latest_recommendation():
    """获取最新投资建议"""
    try:
        theme = request.args.get("theme")
        record = db.get_latest_recommendation(theme=theme)
        if not record:
            return jsonify({"success": True, "data": None})

        return jsonify({
            "success": True,
            "data": {
                "id": record["id"],
                "theme": record["theme"],
                "keywords": record["keywords"],
                "risk_profile": record["risk_profile"],
                "horizon_days": record["horizon_days"],
                "max_articles": record["max_articles"],
                "created_at": format_beijing_time(record["created_at"]),
                "payload": record["payload"],
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/keywords/mine", methods=["POST"])
def mine_keywords():
    """挖掘关键词"""
    try:
        # 获取参数
        data = request.get_json() or {}
        source = data.get("source", "articles")  # articles 或 trends
        hours = data.get("hours", 48)
        min_confidence = data.get("min_confidence", 0.7)
        limit = data.get("limit", 50)
        theme = data.get("theme")
        
        # 挖掘关键词
        if source == "trends":
            keywords = keyword_miner.mine_keywords_from_market_trends(
                market_context=data.get("market_context"),
                theme=theme
            )
        else:
            keywords = keyword_miner.mine_keywords_from_articles(
                hours=hours,
                min_confidence=min_confidence,
                limit=limit,
                theme=theme
            )
        
        # 保存到数据库
        saved_count = 0
        for kw_data in keywords:
            if db.add_mined_keyword(kw_data):
                saved_count += 1
        
        return jsonify({
            "success": True,
            "mined": len(keywords),
            "saved": saved_count,
            "keywords": keywords,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/keywords", methods=["GET"])
def get_mined_keywords():
    """获取挖掘的关键词"""
    try:
        # 获取查询参数
        is_active = request.args.get("active")
        if is_active is not None:
            is_active = is_active.lower() == "true"
        
        min_relevance = request.args.get("min_relevance", type=float)
        limit = request.args.get("limit", type=int, default=100)
        
        # 查询关键词
        keywords = db.get_mined_keywords(
            is_active=is_active,
            min_relevance=min_relevance,
            limit=limit
        )
        
        # 转换为字典
        keywords_data = []
        for kw in keywords:
            keywords_data.append({
                "id": kw.id,
                "keyword": kw.keyword,
                "relevance_score": kw.relevance_score,
                "impact": kw.impact,
                "reasoning": kw.reasoning,
                "source": kw.source,
                "is_active": kw.is_active,
                "usage_count": kw.usage_count or 0,
                "mined_at": format_beijing_time(kw.mined_at),
                "last_used_at": format_beijing_time(kw.last_used_at),
            })
        
        return jsonify({
            "success": True,
            "count": len(keywords_data),
            "keywords": keywords_data,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/keywords/analyze", methods=["POST"])
def analyze_keyword():
    """分析单个关键词的相关性"""
    try:
        data = request.get_json()
        if not data or "keyword" not in data:
            return jsonify({"success": False, "error": "缺少keyword参数"}), 400
        
        keyword = data["keyword"]
        context = data.get("context")
        theme = data.get("theme")
        
        # 分析关键词
        analysis = keyword_miner.analyze_keyword_relevance(keyword, context, theme=theme)
        
        return jsonify({
            "success": True,
            "analysis": analysis,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/keywords/suggested", methods=["GET"])
def get_suggested_keywords():
    """获取建议的关键词列表（用于搜索）"""
    try:
        min_relevance = request.args.get("min_relevance", type=float, default=0.6)
        max_results = request.args.get("max_results", type=int, default=50)
        theme = request.args.get("theme")
        
        # 获取建议关键词
        keywords = keyword_miner.get_suggested_keywords(
            min_relevance=min_relevance,
            max_results=max_results,
            theme=theme
        )
        
        return jsonify({
            "success": True,
            "count": len(keywords),
            "keywords": keywords,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/keywords/invalid", methods=["GET"])
def get_invalid_keywords():
    """获取数据库中无效的关键词列表（仅查询，不删除）"""
    try:
        invalid_keywords = db.get_invalid_keywords()
        
        keywords_data = []
        for kw in invalid_keywords:
            keywords_data.append({
                "id": kw.id,
                "keyword": kw.keyword,
                "relevance_score": kw.relevance_score,
                "impact": kw.impact,
                "source": kw.source,
                "is_active": kw.is_active,
                "usage_count": kw.usage_count or 0,
                "mined_at": format_beijing_time(kw.mined_at),
            })
        
        return jsonify({
            "success": True,
            "count": len(keywords_data),
            "keywords": keywords_data,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/keywords/clean", methods=["POST"])
def clean_invalid_keywords():
    """清理数据库中无效的关键词"""
    try:
        result = db.clean_invalid_keywords()
        
        return jsonify({
            "success": True,
            "message": f"清理完成：删除了 {result['deleted_count']} 个无效关键词",
            **result
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/analysis/price-trend", methods=["GET"])
def analyze_price_trend():
    """分析主题价格涨跌概率"""
    try:
        # 获取最近的高置信度文章
        limit = request.args.get("limit", type=int, default=20)
        hours = request.args.get("hours", type=int, default=168)  # 默认7天
        theme = request.args.get("theme")
        symbols = request.args.get("symbols")
        filter_keywords = search_engine._normalize_keywords(theme=theme) if theme else None
        
        articles = db.get_high_confidence_articles(
            limit=limit,
            min_score=0.7,
            keywords=filter_keywords
        )
        recent_articles = [a for a in articles if a.published_at and 
                          (beijing_now() - to_beijing_time(a.published_at)).total_seconds() / 3600 <= hours]
        
        if not recent_articles:
            return jsonify({
                "success": True,
                "analysis": {
                    "up_probability": 50.0,
                    "down_probability": 50.0,
                    "neutral_probability": 0.0,
                    "summary": "暂无足够的高置信度数据进行分析",
                    "factors": [],
                    "confidence": "low",
                }
            })
        
        # 获取股市行情作为辅助分析
        stock_data = search_engine.fetch_stock_market_info(symbols=symbols)
        market_context = search_engine.build_stock_market_context(stock_data)

        # 使用AI分析涨跌概率
        analysis_result = evaluator.analyze_price_trend(
            recent_articles,
            theme=theme,
            market_context=market_context
        )

        return jsonify({
            "success": True,
            "analysis": analysis_result,
            "articles_count": len(recent_articles),
            "stock_market": stock_data,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/market/stock", methods=["GET"])
def get_stock_market_info():
    """获取股市行情信息"""
    try:
        symbols = request.args.get("symbols")
        stock_data = search_engine.fetch_stock_market_info(symbols=symbols)
        return jsonify({
            "success": stock_data.get("success", False),
            "market": stock_data,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stocks/identified", methods=["GET"])
def get_identified_stocks():
    """获取识别的股票列表"""
    try:
        is_active = request.args.get("active")
        if is_active is not None:
            is_active = is_active.lower() == "true"
        
        theme = request.args.get("theme")
        limit = request.args.get("limit", type=int, default=100)
        
        stock_type = request.args.get("stock_type")  # 可选：us_stock, a_stock, futures
        
        stocks = db.get_identified_stocks(
            is_active=is_active,
            theme=theme,
            stock_type=stock_type,
            limit=limit
        )
        
        stocks_data = []
        for stock in stocks:
            stocks_data.append({
                "id": stock.id,
                "symbol": stock.symbol,
                "company_name": stock.company_name,
                "stock_type": stock.stock_type or "us_stock",
                "market": stock.market,
                "relevance": stock.relevance,
                "theme": stock.theme,
                "source": stock.source,
                "is_active": stock.is_active,
                "identified_at": format_beijing_time(stock.identified_at),
                "last_updated_at": format_beijing_time(stock.last_updated_at),
            })
        
        return jsonify({
            "success": True,
            "count": len(stocks_data),
            "stocks": stocks_data,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stocks/identify", methods=["POST"])
def identify_stocks():
    """手动触发股票识别"""
    try:
        data = request.get_json() or {}
        source = data.get("source", "keywords")  # keywords 或 articles
        theme = data.get("theme")
        
        stocks = []
        if source == "articles":
            limit = data.get("limit", 20)
            articles = db.get_high_confidence_articles(limit=limit, min_score=0.7)
            stocks = stock_identifier.identify_stocks_from_articles(articles, theme=theme, limit=limit)
        else:
            active_keywords = db.get_mined_keywords(is_active=True, min_relevance=0.6, limit=50)
            keyword_list = [kw.keyword for kw in active_keywords]
            stocks = stock_identifier.identify_stocks_from_keywords(keyword_list, theme=theme)
        
        # 保存到数据库
        saved_count = 0
        for stock_data in stocks:
            if db.add_identified_stock(stock_data):
                saved_count += 1
        
        return jsonify({
            "success": True,
            "identified": len(stocks),
            "saved": saved_count,
            "stocks": stocks,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stocks/<symbol>/price", methods=["GET"])
def get_stock_price(symbol):
    """获取股票实时价格（优先使用数据库，可选实时更新）"""
    try:
        stock_type = request.args.get("type")  # 可选：us_stock, a_stock, futures
        force_refresh = request.args.get("refresh", "false").lower() == "true"  # 是否强制刷新
        
        # 先尝试从数据库获取最新价格
        latest_price = db.get_latest_stock_price(symbol)
        
        # 如果数据库中有价格且不是强制刷新，且价格在1小时内，直接返回
        if latest_price and not force_refresh:
            price_age_hours = (beijing_now() - to_beijing_time(latest_price.timestamp)).total_seconds() / 3600
            if price_age_hours < 1:  # 1小时内的价格认为可用
                return jsonify({
                    "success": True,
                    "price": {
                        "symbol": latest_price.symbol,
                        "price": latest_price.price,
                        "change": latest_price.change,
                        "change_percent": latest_price.change_percent,
                        "volume": latest_price.volume,
                        "timestamp": format_beijing_time(latest_price.timestamp),
                        "source": latest_price.source or "database",
                    },
                    "cached": True
                })
        
        # 尝试获取实时价格（仅在强制刷新或数据库无数据时）
        if force_refresh or not latest_price:
            price_data = stock_fetcher.fetch_realtime_price(symbol, stock_type=stock_type)
            if price_data:
                return jsonify({
                    "success": True,
                    "price": price_data,
                    "cached": False
                })
        
        # 如果无法获取实时价格，返回数据库中的最新价格
        if latest_price:
            return jsonify({
                "success": True,
                "price": {
                    "symbol": latest_price.symbol,
                    "price": latest_price.price,
                    "change": latest_price.change,
                    "change_percent": latest_price.change_percent,
                    "volume": latest_price.volume,
                    "timestamp": format_beijing_time(latest_price.timestamp),
                    "source": latest_price.source or "database",
                },
                "cached": True,
                "note": "使用数据库中的最新价格（可能不是实时数据）"
            })
        else:
            # 如果既没有实时价格也没有历史价格，返回错误信息但不返回404
            return jsonify({
                "success": False,
                "error": "无法获取股票价格，请检查股票代码或API配置",
                "symbol": symbol.upper()
            }), 200  # 改为200，让前端可以处理错误信息
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "symbol": symbol.upper()}), 200


@app.route("/api/stocks/prices/batch", methods=["POST"])
def get_stock_prices_batch():
    """批量获取股票价格（优先使用数据库）"""
    try:
        data = request.get_json() or {}
        symbols = data.get("symbols", [])  # 股票代码列表
        stock_types = data.get("stock_types", {})  # {symbol: stock_type} 映射
        force_refresh = data.get("force_refresh", False)  # 是否强制刷新
        
        if not symbols:
            return jsonify({"success": False, "error": "请提供股票代码列表"}), 400
        
        results = {}
        
        # 批量从数据库获取最新价格
        for symbol in symbols:
            symbol_upper = symbol.upper()
            stock_type = stock_types.get(symbol) or stock_types.get(symbol_upper)
            
            try:
                latest_price = db.get_latest_stock_price(symbol_upper)
                
                # 如果数据库中有价格且不是强制刷新，且价格在1小时内，使用数据库价格
                if latest_price and not force_refresh:
                    price_age_hours = (beijing_now() - to_beijing_time(latest_price.timestamp)).total_seconds() / 3600
                    if price_age_hours < 1:  # 1小时内的价格认为可用
                        results[symbol_upper] = {
                            "success": True,
                            "price": {
                                "symbol": latest_price.symbol,
                                "price": latest_price.price,
                                "change": latest_price.change,
                                "change_percent": latest_price.change_percent,
                                "volume": latest_price.volume,
                                "timestamp": format_beijing_time(latest_price.timestamp),
                                "source": latest_price.source or "database",
                            },
                            "cached": True
                        }
                        continue
                
                # 尝试获取实时价格（仅在强制刷新或数据库无数据时）
                if force_refresh or not latest_price:
                    price_data = stock_fetcher.fetch_realtime_price(symbol_upper, stock_type=stock_type)
                    if price_data:
                        results[symbol_upper] = {
                            "success": True,
                            "price": price_data,
                            "cached": False
                        }
                        continue
                
                # 如果无法获取实时价格，使用数据库中的最新价格
                if latest_price:
                    results[symbol_upper] = {
                        "success": True,
                        "price": {
                            "symbol": latest_price.symbol,
                            "price": latest_price.price,
                            "change": latest_price.change,
                            "change_percent": latest_price.change_percent,
                            "volume": latest_price.volume,
                            "timestamp": format_beijing_time(latest_price.timestamp),
                            "source": latest_price.source or "database",
                        },
                        "cached": True
                    }
                else:
                    results[symbol_upper] = {
                        "success": False,
                        "error": "无法获取股票价格"
                    }
            except Exception as e:
                results[symbol_upper] = {
                    "success": False,
                    "error": str(e)
                }
        
        return jsonify({
            "success": True,
            "results": results
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stocks/<symbol>/chart", methods=["GET"])
def get_stock_chart_data(symbol):
    """获取股票走势图数据"""
    try:
        chart_type = request.args.get("type", "daily")  # daily 或 intraday
        days = request.args.get("days", type=int, default=30)
        interval = request.args.get("interval", "5min")
        
        if chart_type == "intraday":
            data = stock_fetcher.fetch_intraday_data(symbol, interval=interval)
        else:
            data = stock_fetcher.fetch_daily_data(symbol, days=days)
        
        if data:
            return jsonify({
                "success": True,
                "symbol": symbol.upper(),
                "data": data,
                "type": chart_type,
            })
        else:
            return jsonify({
                "success": False,
                "error": "无法获取股票走势数据，请检查股票代码或API配置",
            }), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stocks/<symbol>/history", methods=["GET"])
def get_stock_price_history(symbol):
    """获取股票价格历史（从数据库）"""
    try:
        hours = request.args.get("hours", type=int, default=24)
        limit = request.args.get("limit", type=int, default=100)
        
        prices = db.get_stock_prices(symbol, hours=hours, limit=limit)
        
        prices_data = []
        for price in prices:
            prices_data.append({
                "id": price.id,
                "symbol": price.symbol,
                "price": price.price,
                "change": price.change,
                "change_percent": price.change_percent,
                "volume": price.volume,
                "timestamp": format_beijing_time(price.timestamp),
                "source": price.source,
            })
        
        return jsonify({
            "success": True,
            "count": len(prices_data),
            "prices": prices_data,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/stocks/update", methods=["POST"])
def update_stock_prices():
    """手动触发股票价格更新"""
    try:
        data = request.get_json() or {}
        symbols = data.get("symbols")  # 可选，如果不提供则更新所有活跃股票
        
        if symbols:
            symbols_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        else:
            active_stocks = db.get_identified_stocks(is_active=True, limit=50)
            symbols_list = [stock.symbol for stock in active_stocks]
        
        updated_count = 0
        results = {}
        for symbol in symbols_list:
            # 从数据库获取股票类型
            stock = db.get_identified_stocks(limit=1000)
            stock_type = None
            for s in stock:
                if s.symbol == symbol:
                    stock_type = s.stock_type
                    break
            
            price_data = stock_fetcher.fetch_realtime_price(symbol, stock_type=stock_type)
            if price_data:
                updated_count += 1
                results[symbol] = price_data
        
        return jsonify({
            "success": True,
            "updated": updated_count,
            "total": len(symbols_list),
            "results": results,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    import os
    
    print("启动Flask API服务...")
    print(f"API将在 http://localhost:5000 上运行")
    
    # 检测AI API连接
    print("正在检测AI API连接...")
    success, message = evaluator.test_connection()
    if success:
        print(f"✓ {message}")
    else:
        print(f"⚠ {message}")
        print("提示：API服务将继续运行，但AI评估功能可能不可用")
        print("     所有文章的置信度分数将使用默认值（0.5）\n")
    
    # 启动后台定时任务（实时持续获取信息源并进行分析）
    # 注意：Flask debug模式下的reloader可能会重启进程，但调度器有运行状态检查，不会重复启动
    print("启动后台信息采集任务...")
    scheduler.start(run_immediately=True)
    print("后台任务已启动，系统将每 {} 分钟自动搜索和分析新信息".format(Config.SEARCH_INTERVAL_MINUTES))
    
    # 启动Flask应用
    # 使用use_reloader=False避免在生产环境中重复启动调度器
    # 如果需要热重载，可以设置环境变量FLASK_ENV=development
    use_reloader = os.getenv("FLASK_ENV") == "development" and os.getenv("USE_RELOADER", "false").lower() == "true"
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=use_reloader)
