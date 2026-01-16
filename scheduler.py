"""定时任务调度器"""
import schedule
import time
import threading
from datetime import datetime, timezone, timedelta
from search_engine import SearchEngine
from confidence_evaluator import ConfidenceEvaluator
from keyword_miner import KeywordMiner
from stock_identifier import StockIdentifier
from stock_fetcher import StockFetcher
from multi_agent import MultiAgentOrchestrator
from database import db
from config import Config

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


class Scheduler:
    """定时任务调度器类"""
    
    def __init__(self):
        self.search_engine = SearchEngine()
        self.evaluator = ConfidenceEvaluator()
        self.keyword_miner = KeywordMiner()
        self.stock_identifier = StockIdentifier()
        self.stock_fetcher = StockFetcher()
        self.multi_agent = MultiAgentOrchestrator()
        self.running = False
        self.thread = None
        self.started_at = None
        self.lock = threading.Lock()
        self.jobs = {}
        self.task_definitions = {
            "search_and_evaluate": {
                "label": "信息检索与评估",
                "interval": f"每 {Config.SEARCH_INTERVAL_MINUTES} 分钟",
            },
            "mine_keywords": {
                "label": "关键词自动挖掘",
                "interval": f"每 {Config.KEYWORD_MINING_INTERVAL_HOURS} 小时",
            },
            "identify_stocks": {
                "label": "股票识别",
                "interval": "每 2 小时",
            },
            "update_stock_prices": {
                "label": "股票价格更新",
                "interval": "每 30 分钟",
            },
            "generate_recommendation": {
                "label": "投资建议生成",
                "interval": f"每 {Config.RECOMMENDATION_INTERVAL_MINUTES} 分钟",
            },
        }
        self.task_state = {
            key: {
                "last_run": None,
                "last_started_at": None,
                "last_duration_seconds": None,
                "last_status": "idle",
                "last_error": None,
                "is_running": False,
            }
            for key in self.task_definitions
        }

    def _run_task(self, task_name, task_func):
        start_time = beijing_now()
        with self.lock:
            state = self.task_state[task_name]
            state["is_running"] = True
            state["last_started_at"] = start_time
            state["last_status"] = "running"
            state["last_error"] = None

        error_message = None
        try:
            task_func()
        except Exception as exc:
            error_message = str(exc)
            print(f"任务 {task_name} 执行出错: {error_message}")
        finally:
            end_time = beijing_now()
            duration = (end_time - start_time).total_seconds()
            with self.lock:
                state = self.task_state[task_name]
                state["is_running"] = False
                state["last_run"] = end_time
                state["last_duration_seconds"] = duration
                if error_message:
                    state["last_status"] = "error"
                    state["last_error"] = error_message
                else:
                    state["last_status"] = "success"
    
    def search_and_evaluate(self):
        """执行搜索和评估任务"""
        print(f"\n[{beijing_now().strftime('%Y-%m-%d %H:%M:%S')}] 开始搜索新信息...")
        
        try:
            # 从数据库获取活跃的挖掘关键词
            active_keywords = db.get_mined_keywords(is_active=True, min_relevance=0.6, limit=30)
            keyword_list = [kw.keyword for kw in active_keywords] if active_keywords else None
            
            if keyword_list:
                print(f"使用 {len(keyword_list)} 个挖掘的关键词进行搜索: {', '.join(keyword_list[:5])}{'...' if len(keyword_list) > 5 else ''}")
            else:
                print("未找到活跃的挖掘关键词，使用默认关键词")
            
            # 搜索文章（使用挖掘的关键词）
            articles = self.search_engine.search_all(
                Config.MAX_ARTICLES_PER_SEARCH,
                theme=Config.DEFAULT_THEME,
                keywords=keyword_list
            )
            print(f"找到 {len(articles)} 篇文章")
            
            # 过滤已存在的文章，避免重复评估
            urls = [article.get("url") for article in articles if article.get("url")]
            existing_urls = db.get_existing_article_urls(urls)
            new_articles = [
                article for article in articles
                if article.get("url") not in existing_urls
            ]

            if not new_articles:
                print("没有新的文章需要评估")
                return

            # 评估并保存
            saved_count = 0
            high_confidence_count = 0
            
            for article in new_articles:
                # 评估置信度
                evaluation = self.evaluator.evaluate(article)
                
                # 合并数据
                article_data = {
                    **article,
                    **evaluation,
                }
                
                # 保存到数据库
                saved_article = db.add_article(article_data)
                if saved_article:
                    saved_count += 1
                    if saved_article.is_high_confidence:
                        high_confidence_count += 1
                        print(f"✓ 高置信度文章: {saved_article.title[:60]}... (置信度: {saved_article.confidence_score:.2f})")
            
            skipped_count = len(articles) - len(new_articles)
            print(f"完成！保存了 {saved_count} 篇文章，其中 {high_confidence_count} 篇为高置信度")
            if skipped_count > 0:
                print(f"已跳过 {skipped_count} 篇已存在文章，避免重复评估")
        except Exception as e:
            print(f"搜索和评估过程中出错: {e}")

    def mine_keywords(self):
        """从高置信度文章中自动挖掘关键词"""
        print(f"\n[{beijing_now().strftime('%Y-%m-%d %H:%M:%S')}] 开始挖掘关键词...")

        try:
            keywords = self.keyword_miner.mine_keywords_from_articles(
                hours=48,
                min_confidence=Config.MIN_CONFIDENCE_SCORE,
                limit=50,
                theme=Config.DEFAULT_THEME,
            )

            if not keywords:
                print("没有挖掘到新的关键词")
                return

            saved_count = 0
            for kw_data in keywords:
                if db.add_mined_keyword(kw_data):
                    saved_count += 1

            print(f"完成！挖掘 {len(keywords)} 个关键词，保存 {saved_count} 个")
        except Exception as e:
            print(f"关键词挖掘过程中出错: {e}")
    
    def identify_stocks(self):
        """执行股票识别任务"""
        print(f"\n[{beijing_now().strftime('%Y-%m-%d %H:%M:%S')}] 开始识别相关股票...")
        
        try:
            # 从高置信度关键词中识别股票
            active_keywords = db.get_mined_keywords(is_active=True, min_relevance=0.6, limit=50)
            if active_keywords:
                keyword_list = [kw.keyword for kw in active_keywords]
                stocks_from_keywords = self.stock_identifier.identify_stocks_from_keywords(
                    keyword_list
                )
                
                # 保存识别的股票
                saved_count = 0
                for stock_data in stocks_from_keywords:
                    if db.add_identified_stock(stock_data):
                        saved_count += 1
                        print(f"✓ 识别股票: {stock_data['symbol']} - {stock_data.get('company_name', 'N/A')}")
                
                print(f"从关键词中识别并保存了 {saved_count} 只股票")
            
            # 从高置信度文章中识别股票
            high_conf_articles = db.get_high_confidence_articles(limit=20, min_score=0.7)
            if high_conf_articles:
                stocks_from_articles = self.stock_identifier.identify_stocks_from_articles(
                    high_conf_articles,
                    limit=20
                )
                
                # 保存识别的股票
                saved_count = 0
                for stock_data in stocks_from_articles:
                    if db.add_identified_stock(stock_data):
                        saved_count += 1
                        print(f"✓ 识别股票: {stock_data['symbol']} - {stock_data.get('company_name', 'N/A')}")
                
                print(f"从文章中识别并保存了 {saved_count} 只股票")
        except Exception as e:
            print(f"股票识别过程中出错: {e}")
    
    def update_stock_prices(self):
        """更新股票价格"""
        print(f"\n[{beijing_now().strftime('%Y-%m-%d %H:%M:%S')}] 开始更新股票价格...")
        
        try:
            # 获取所有活跃的股票
            active_stocks = db.get_identified_stocks(is_active=True, limit=50)
            
            if not active_stocks:
                print("没有需要更新的股票")
                return
            
            updated_count = 0
            for stock in active_stocks:
                price_data = self.stock_fetcher.fetch_realtime_price(stock.symbol)
                if price_data:
                    updated_count += 1
                    print(f"✓ 更新股票价格: {stock.symbol} - ${price_data.get('price', 'N/A')}")
                # 避免API频率限制
                time.sleep(0.5)
            
            print(f"完成！更新了 {updated_count} 只股票的价格")
        except Exception as e:
            print(f"更新股票价格过程中出错: {e}")

    def generate_recommendation(self):
        """生成投资建议并保存"""
        print(f"\n[{beijing_now().strftime('%Y-%m-%d %H:%M:%S')}] 开始生成投资建议...")

        try:
            result = self.multi_agent.run(
                theme=Config.DEFAULT_THEME,
                risk_profile="balanced",
                horizon_days=30,
                max_articles=Config.AGENT_MAX_ARTICLES,
            )

            db.add_recommendation({
                "theme": result["context"]["theme"],
                "keywords": ",".join(result["context"].get("keywords") or []),
                "risk_profile": result["context"]["risk_profile"],
                "horizon_days": result["context"]["horizon_days"],
                "max_articles": result["context"]["max_articles"],
                "payload": result,
            })

            print("投资建议生成完成并已保存")
        except Exception as e:
            print(f"生成投资建议过程中出错: {e}")

    def _run_startup_pipeline(self):
        """程序启动时执行完整流程"""
        print("\n启动后自动执行全流程任务...")
        self._run_task("search_and_evaluate", self.search_and_evaluate)
        self._run_task("mine_keywords", self.mine_keywords)
        self._run_task("identify_stocks", self.identify_stocks)
        self._run_task("update_stock_prices", self.update_stock_prices)
        self._run_task("generate_recommendation", self.generate_recommendation)
    
    def start(self, run_immediately: bool = True):
        """启动定时任务"""
        if self.running:
            print("调度器已在运行")
            return

        # 设置定时任务
        self.jobs["search_and_evaluate"] = schedule.every(
            Config.SEARCH_INTERVAL_MINUTES
        ).minutes.do(lambda: self._run_task("search_and_evaluate", self.search_and_evaluate))
        self.jobs["mine_keywords"] = schedule.every(
            Config.KEYWORD_MINING_INTERVAL_HOURS
        ).hours.do(lambda: self._run_task("mine_keywords", self.mine_keywords))
        # 股票识别任务（每2小时执行一次）
        self.jobs["identify_stocks"] = schedule.every(2).hours.do(
            lambda: self._run_task("identify_stocks", self.identify_stocks)
        )
        # 股票价格更新任务（每30分钟执行一次）
        self.jobs["update_stock_prices"] = schedule.every(30).minutes.do(
            lambda: self._run_task("update_stock_prices", self.update_stock_prices)
        )
        self.jobs["generate_recommendation"] = schedule.every(
            Config.RECOMMENDATION_INTERVAL_MINUTES
        ).minutes.do(lambda: self._run_task("generate_recommendation", self.generate_recommendation))
        
        self.running = True
        self.started_at = beijing_now()
        
        def run_scheduler():
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
        
        self.thread = threading.Thread(target=run_scheduler, daemon=True)
        self.thread.start()

        # 立即执行完整流程（可选）
        if run_immediately:
            threading.Thread(target=self._run_startup_pipeline, daemon=True).start()
        
        print(f"定时任务已启动，每 {Config.SEARCH_INTERVAL_MINUTES} 分钟执行一次搜索")
    
    def stop(self):
        """停止定时任务"""
        self.running = False
        self.started_at = None
        schedule.clear()
        print("定时任务已停止")

    def get_status(self):
        """获取调度器状态"""
        now = beijing_now()
        tasks = []
        with self.lock:
            for task_name, definition in self.task_definitions.items():
                state = self.task_state[task_name]
                job = self.jobs.get(task_name)
                next_run = job.next_run if job else None
                tasks.append({
                    "name": task_name,
                    "label": definition["label"],
                    "interval": definition["interval"],
                    "last_run": format_beijing_time(state["last_run"]),
                    "last_started_at": format_beijing_time(state["last_started_at"]),
                    "last_duration_seconds": state["last_duration_seconds"],
                    "last_status": state["last_status"],
                    "last_error": state["last_error"],
                    "is_running": state["is_running"],
                    "next_run": format_beijing_time(next_run),
                })

        return {
            "running": self.running,
            "started_at": format_beijing_time(self.started_at),
            "server_time": now.isoformat(),
            "tasks": tasks,
        }
