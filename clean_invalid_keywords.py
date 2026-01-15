"""清理数据库中无效关键词的脚本"""
from database import db

def main():
    """主函数：清理无效关键词"""
    print("=" * 60)
    print("清理无效关键词工具")
    print("=" * 60)
    print()
    
    # 1. 先查看无效关键词
    print("📋 正在查找无效关键词...")
    invalid_keywords = db.get_invalid_keywords()
    
    if not invalid_keywords:
        print("✅ 没有发现无效关键词，数据库很干净！")
        return
    
    print(f"\n⚠️  发现 {len(invalid_keywords)} 个无效关键词：\n")
    for i, kw in enumerate(invalid_keywords, 1):
        print(f"{i}. {kw.keyword}")
        print(f"   ID: {kw.id}, 相关性: {kw.relevance_score:.2f}, 来源: {kw.source}")
        print()
    
    # 2. 确认是否清理
    print("=" * 60)
    response = input(f"是否删除这 {len(invalid_keywords)} 个无效关键词？(y/n): ").strip().lower()
    
    if response not in ['y', 'yes', '是']:
        print("❌ 已取消清理操作")
        return
    
    # 3. 执行清理
    print("\n🗑️  正在清理无效关键词...")
    result = db.clean_invalid_keywords()
    
    # 4. 显示结果
    print("\n" + "=" * 60)
    print("清理结果：")
    print("=" * 60)
    print(f"总关键词数: {result['total_keywords']}")
    print(f"无效关键词数: {result['invalid_keywords']}")
    print(f"已删除数: {result['deleted_count']}")
    print(f"剩余关键词数: {result['remaining_keywords']}")
    print()
    
    if result['deleted_count'] > 0:
        print("✅ 清理完成！")
    else:
        print("ℹ️  没有需要清理的关键词")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 操作已取消")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
