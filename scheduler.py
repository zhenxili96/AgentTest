"""定时任务调度器"""
import schedule
import time
import threading
from datetime import datetime
from search_engine import SearchEngine
from confidence_evaluator import ConfidenceEvaluator
from database import db
from config import Config


class Scheduler:
    """定时任务调度器类"""
    
    def __init__(self):
        self.search_engine = SearchEngine()
        self.evaluator = ConfidenceEvaluator()
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
