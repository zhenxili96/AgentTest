"""定时任务调度器"""
import schedule
import time
import threading
from datetime import datetime
from search_engine import SearchEngine
from confidence_evaluator import ConfidenceEvaluator
from keyword_miner import KeywordMiner
from stock_identifier import StockIdentifier
from stock_fetcher import StockFetcher
from database import db
from config import Config


class Scheduler:
    """定时任务调度器类"""
    
    def __init__(self):
        self.search_engine = SearchEngine()
        self.evaluator = ConfidenceEvaluator()
        self.keyword_miner = KeywordMiner()
        self.stock_identifier = StockIdentifier()
        self.stock_fetcher = StockFetcher()
        self.running = False
        self.thread = None
    
    def search_and_evaluate(self):
        """执行搜索和评估任务"""
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始搜索新信息...")
        
        try:
            # 搜索文章
            articles = self.search_engine.search_all(Config.MAX_ARTICLES_PER_SEARCH)
            print(f"找到 {len(articles)} 篇文章")
            
            # 评估并保存
            saved_count = 0
            high_confidence_count = 0
            
            for article in articles:
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
            
            print(f"完成！保存了 {saved_count} 篇文章，其中 {high_confidence_count} 篇为高置信度")
        except Exception as e:
            print(f"搜索和评估过程中出错: {e}")
    
    def identify_stocks(self):
        """执行股票识别任务"""
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始识别相关股票...")
        
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
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始更新股票价格...")
        
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
    
    def start(self, run_immediately: bool = True):
        """启动定时任务"""
        if self.running:
            print("调度器已在运行")
            return
        
        # 立即执行一次（可选）
        if run_immediately:
            self.search_and_evaluate()
        
        # 设置定时任务
        schedule.every(Config.SEARCH_INTERVAL_MINUTES).minutes.do(self.search_and_evaluate)
        # 股票识别任务（每2小时执行一次）
        schedule.every(2).hours.do(self.identify_stocks)
        # 股票价格更新任务（每30分钟执行一次）
        schedule.every(30).minutes.do(self.update_stock_prices)
        
        self.running = True
        
        def run_scheduler():
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
        
        self.thread = threading.Thread(target=run_scheduler, daemon=True)
        self.thread.start()
        
        print(f"定时任务已启动，每 {Config.SEARCH_INTERVAL_MINUTES} 分钟执行一次搜索")
    
    def stop(self):
        """停止定时任务"""
        self.running = False
        schedule.clear()
        print("定时任务已停止")
