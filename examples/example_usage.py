"""使用示例脚本"""
from search_engine import SearchEngine
from confidence_evaluator import ConfidenceEvaluator
from database import db
from config import Config


def example_search_and_evaluate():
    """示例：搜索和评估文章"""
    print("=== 示例：搜索和评估文章 ===\n")
    
    # 创建搜索引擎
    search_engine = SearchEngine()
    evaluator = ConfidenceEvaluator()
    
    # 搜索文章
    print("正在搜索文章...")
    articles = search_engine.search_all(max_results=10)
    print(f"找到 {len(articles)} 篇文章\n")
    
    # 评估并显示前3篇
    for i, article in enumerate(articles[:3], 1):
        print(f"\n--- 文章 {i} ---")
        print(f"标题: {article['title']}")
        print(f"来源: {article['source']}")
        print(f"URL: {article['url']}")
        
        # 评估
        evaluation = evaluator.evaluate(article)
        print(f"\n评估结果:")
        print(f"  相关性分数: {evaluation['relevance_score']:.2f}")
        print(f"  可靠性分数: {evaluation['reliability_score']:.2f}")
        print(f"  置信度分数: {evaluation['confidence_score']:.2f}")
        print(f"  高置信度: {'是' if evaluation['is_high_confidence'] else '否'}")
        print(f"  AI分析: {evaluation['ai_analysis'][:200]}...")


def example_query_database():
    """示例：查询数据库"""
    print("\n\n=== 示例：查询数据库 ===\n")
    
    # 获取高置信度文章
    high_confidence = db.get_high_confidence_articles(limit=5)
    print(f"高置信度文章数量: {len(high_confidence)}")
    
    for article in high_confidence:
        print(f"\n- {article.title[:60]}...")
        print(f"  置信度: {article.confidence_score:.2f}")
        print(f"  来源: {article.source}")
    
    # 获取统计信息
    stats = db.get_article_stats()
    print(f"\n统计信息:")
    print(f"  总文章数: {stats['total_articles']}")
    print(f"  高置信度文章数: {stats['high_confidence_articles']}")
    print(f"  平均置信度: {stats['average_confidence']:.2f}")


if __name__ == "__main__":
    # 验证配置
    if not Config.validate():
        print("警告：配置未完全设置，某些功能可能无法正常工作")
    
    # 运行示例
    try:
        example_search_and_evaluate()
        example_query_database()
    except Exception as e:
        print(f"运行示例时出错: {e}")
