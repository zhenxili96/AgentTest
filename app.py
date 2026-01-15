"""Flask API服务"""
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from datetime import datetime, timedelta
from database import db
from search_engine import SearchEngine
from confidence_evaluator import ConfidenceEvaluator
from keyword_miner import KeywordMiner
from scheduler import Scheduler
from config import Config

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

search_engine = SearchEngine()
evaluator = ConfidenceEvaluator()
keyword_miner = KeywordMiner()

# 初始化调度器（用于后台持续获取信息）
scheduler = Scheduler()


@app.route("/")
def index():
    """主页"""
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def health():
    """健康检查"""
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})


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
                "published_at": article.published_at.isoformat() if article.published_at else None,
                "confidence_score": article.confidence_score,
                "relevance_score": article.relevance_score,
                "reliability_score": article.reliability_score,
                "ai_analysis": article.ai_analysis,
                "keywords": article.keywords,
                "is_high_confidence": article.is_high_confidence,
                "created_at": article.created_at.isoformat() if article.created_at else None,
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
        if ai_provider == "openrouter":
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
        
        # 评估并保存
        saved_count = 0
        for article in articles:
            evaluation = evaluator.evaluate(article, theme=theme)
            article_data = {**article, **evaluation}
            if db.add_article(article_data):
                saved_count += 1
        
        return jsonify({
            "success": True,
            "found": len(articles),
            "saved": saved_count,
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
                "mined_at": kw.mined_at.isoformat() if kw.mined_at else None,
                "last_used_at": kw.last_used_at.isoformat() if kw.last_used_at else None,
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
                          (datetime.utcnow() - a.published_at).total_seconds() / 3600 <= hours]
        
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


if __name__ == "__main__":
    import os
    
    print("启动Flask API服务...")
    print(f"API将在 http://localhost:5000 上运行")
    
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
