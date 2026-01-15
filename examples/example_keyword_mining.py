"""关键词挖掘使用示例"""
from keyword_miner import KeywordMiner
from database import db


def example_mine_from_articles():
    """示例：从高置信度文章中挖掘关键词"""
    print("=" * 60)
    print("示例1：从高置信度文章中挖掘关键词")
    print("=" * 60)
    
    miner = KeywordMiner()
    
    # 从最近48小时的高置信度文章中挖掘关键词
    keywords = miner.mine_keywords_from_articles(
        hours=48,
        min_confidence=0.7,
        limit=50
    )
    
    print(f"\n挖掘到 {len(keywords)} 个关键词：\n")
    for i, kw in enumerate(keywords[:10], 1):  # 显示前10个
        print(f"{i}. {kw['keyword']}")
        print(f"   相关性: {kw['relevance_score']:.2f}")
        print(f"   影响: {kw['impact']}")
        print(f"   说明: {kw.get('reasoning', '')[:100]}")
        print()
    
    # 保存到数据库
    saved_count = 0
    for kw_data in keywords:
        if db.add_mined_keyword(kw_data):
            saved_count += 1
    
    print(f"已保存 {saved_count} 个关键词到数据库\n")


def example_mine_from_trends():
    """示例：从市场趋势中挖掘关键词"""
    print("=" * 60)
    print("示例2：从市场趋势中挖掘关键词")
    print("=" * 60)
    
    miner = KeywordMiner()
    
    # 从市场趋势中挖掘关键词
    keywords = miner.mine_keywords_from_market_trends()
    
    print(f"\n从市场趋势中挖掘到 {len(keywords)} 个关键词：\n")
    for i, kw in enumerate(keywords[:10], 1):  # 显示前10个
        print(f"{i}. {kw['keyword']}")
        print(f"   相关性: {kw['relevance_score']:.2f}")
        print(f"   影响: {kw['impact']}")
        print(f"   说明: {kw.get('reasoning', '')[:100]}")
        print()
    
    # 保存到数据库
    saved_count = 0
    for kw_data in keywords:
        if db.add_mined_keyword(kw_data):
            saved_count += 1
    
    print(f"已保存 {saved_count} 个关键词到数据库\n")


def example_analyze_keyword():
    """示例：分析单个关键词的相关性"""
    print("=" * 60)
    print("示例3：分析单个关键词的相关性")
    print("=" * 60)
    
    miner = KeywordMiner()
    
    # 分析关键词
    test_keywords = ["美联储加息", "光伏产业", "地缘政治风险"]
    
    for keyword in test_keywords:
        print(f"\n分析关键词: {keyword}")
        analysis = miner.analyze_keyword_relevance(keyword)
        
        print(f"相关性分数: {analysis['relevance_score']:.2f}")
        print(f"影响方向: {analysis['impact']}")
        print(f"分析说明: {analysis['reasoning'][:200]}")
        print()


def example_get_suggested_keywords():
    """示例：获取建议的关键词列表"""
    print("=" * 60)
    print("示例4：获取建议的关键词列表")
    print("=" * 60)
    
    miner = KeywordMiner()
    
    # 获取建议的关键词
    keywords = miner.get_suggested_keywords(
        min_relevance=0.6,
        max_results=20
    )
    
    print(f"\n建议的关键词列表（共 {len(keywords)} 个）：\n")
    for i, kw in enumerate(keywords, 1):
        print(f"{i}. {kw}")
    
    print(f"\n可以用于更新搜索关键词配置：")
    print(f"SEARCH_KEYWORDS={','.join(keywords)}")


def example_get_mined_keywords_from_db():
    """示例：从数据库获取已挖掘的关键词"""
    print("=" * 60)
    print("示例5：从数据库获取已挖掘的关键词")
    print("=" * 60)
    
    # 获取所有活跃的关键词
    keywords = db.get_mined_keywords(
        is_active=True,
        min_relevance=0.6,
        limit=20
    )
    
    print(f"\n数据库中已挖掘的关键词（共 {len(keywords)} 个）：\n")
    for i, kw in enumerate(keywords, 1):
        print(f"{i}. {kw.keyword}")
        print(f"   相关性: {kw.relevance_score:.2f}")
        print(f"   影响: {kw.impact}")
        print(f"   使用次数: {kw.usage_count or 0}")
        print(f"   挖掘时间: {kw.mined_at}")
        print()


if __name__ == "__main__":
    print("\n关键词挖掘Agent使用示例\n")
    
    try:
        # 运行示例
        example_mine_from_articles()
        example_mine_from_trends()
        example_analyze_keyword()
        example_get_suggested_keywords()
        example_get_mined_keywords_from_db()
        
        print("\n" + "=" * 60)
        print("所有示例运行完成！")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()
