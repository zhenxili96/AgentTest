"""数据库迁移脚本：为 identified_stocks 表添加 stock_type 列"""
import sqlite3
from config import Config
import os

def migrate_database():
    """执行数据库迁移"""
    db_path = Config.DATABASE_URL.replace("sqlite:///", "")
    
    if not os.path.exists(db_path):
        print(f"[错误] 数据库文件不存在: {db_path}")
        return False
    
    print(f"[信息] 正在迁移数据库: {db_path}")
    print("=" * 60)
    
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查 stock_type 列是否已存在
        cursor.execute("PRAGMA table_info(identified_stocks)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "stock_type" in columns:
            print("[成功] stock_type 列已存在，无需迁移")
            conn.close()
            return True
        
        print("[警告] 检测到缺少 stock_type 列，开始迁移...")
        
        # 添加 stock_type 列
        print("1. 添加 stock_type 列...")
        cursor.execute("""
            ALTER TABLE identified_stocks 
            ADD COLUMN stock_type VARCHAR(20) DEFAULT 'us_stock'
        """)
        
        # 创建索引（如果不存在）
        print("2. 创建 stock_type 索引...")
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS ix_identified_stocks_stock_type 
                ON identified_stocks(stock_type)
            """)
        except sqlite3.OperationalError as e:
            if "already exists" not in str(e).lower():
                raise
        
        # 提交更改
        conn.commit()
        print("[成功] 迁移完成！")
        
        # 验证迁移结果
        cursor.execute("PRAGMA table_info(identified_stocks)")
        columns_after = [row[1] for row in cursor.fetchall()]
        
        if "stock_type" in columns_after:
            print("[成功] 验证成功：stock_type 列已添加")
            conn.close()
            return True
        else:
            print("[错误] 验证失败：stock_type 列未成功添加")
            conn.close()
            return False
            
    except sqlite3.OperationalError as e:
        print(f"[错误] 迁移出错: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False
    except Exception as e:
        print(f"[错误] 发生未知错误: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.close()
        return False


if __name__ == "__main__":
    print("\n数据库迁移工具：添加 stock_type 列\n")
    
    success = migrate_database()
    
    if success:
        print("\n" + "=" * 60)
        print("[成功] 迁移成功！现在可以正常使用系统了")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("[错误] 迁移失败，请检查错误信息")
        print("=" * 60)
        exit(1)
