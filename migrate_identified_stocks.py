"""数据库迁移脚本：为 identified_stocks 表添加所有缺失的列"""
import sqlite3
from config import Config
import os

# 定义所有需要的列及其类型
REQUIRED_COLUMNS = {
    "stock_type": ("VARCHAR(20)", "'us_stock'"),
    "market": ("VARCHAR(50)", "NULL"),
    "relevance": ("TEXT", "NULL"),
    "theme": ("VARCHAR(100)", "NULL"),
    "source": ("VARCHAR(100)", "NULL"),
    "is_active": ("BOOLEAN", "1"),
    "identified_at": ("DATETIME", "CURRENT_TIMESTAMP"),
    "last_updated_at": ("DATETIME", "NULL"),
}

# 需要创建索引的列
INDEX_COLUMNS = ["stock_type", "is_active", "identified_at"]


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
        
        # 检查表是否存在
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='identified_stocks'
        """)
        if not cursor.fetchone():
            print("[错误] identified_stocks 表不存在")
            conn.close()
            return False
        
        # 获取现有列
        cursor.execute("PRAGMA table_info(identified_stocks)")
        existing_columns = {row[1]: row for row in cursor.fetchall()}
        existing_column_names = set(existing_columns.keys())
        
        print(f"[信息] 现有列: {', '.join(sorted(existing_column_names))}")
        print()
        
        # 检查并添加缺失的列
        added_columns = []
        for column_name, (column_type, default_value) in REQUIRED_COLUMNS.items():
            if column_name not in existing_column_names:
                print(f"[迁移] 添加列: {column_name} ({column_type})")
                try:
                    if default_value == "NULL":
                        sql = f"ALTER TABLE identified_stocks ADD COLUMN {column_name} {column_type}"
                    elif default_value == "CURRENT_TIMESTAMP":
                        # SQLite 不支持 CURRENT_TIMESTAMP 作为默认值，使用 NULL
                        sql = f"ALTER TABLE identified_stocks ADD COLUMN {column_name} {column_type}"
                    else:
                        sql = f"ALTER TABLE identified_stocks ADD COLUMN {column_name} {column_type} DEFAULT {default_value}"
                    
                    cursor.execute(sql)
                    added_columns.append(column_name)
                except sqlite3.OperationalError as e:
                    print(f"[警告] 添加列 {column_name} 失败: {e}")
            else:
                print(f"[跳过] 列 {column_name} 已存在")
        
        # 创建索引
        print()
        print("[信息] 检查索引...")
        for column_name in INDEX_COLUMNS:
            if column_name in existing_column_names or column_name in added_columns:
                index_name = f"ix_identified_stocks_{column_name}"
                try:
                    cursor.execute(f"""
                        CREATE INDEX IF NOT EXISTS {index_name} 
                        ON identified_stocks({column_name})
                    """)
                    print(f"[成功] 索引 {index_name} 已创建或已存在")
                except sqlite3.OperationalError as e:
                    if "already exists" not in str(e).lower():
                        print(f"[警告] 创建索引 {index_name} 失败: {e}")
        
        # 提交更改
        conn.commit()
        
        # 验证迁移结果
        print()
        print("[信息] 验证迁移结果...")
        cursor.execute("PRAGMA table_info(identified_stocks)")
        columns_after = {row[1]: row for row in cursor.fetchall()}
        column_names_after = set(columns_after.keys())
        
        all_present = all(col in column_names_after for col in REQUIRED_COLUMNS.keys())
        
        if all_present:
            print("[成功] 所有必需的列都已存在")
            if added_columns:
                print(f"[成功] 成功添加了 {len(added_columns)} 个列: {', '.join(added_columns)}")
            else:
                print("[信息] 无需添加新列")
            conn.close()
            return True
        else:
            missing = set(REQUIRED_COLUMNS.keys()) - column_names_after
            print(f"[错误] 以下列仍然缺失: {', '.join(missing)}")
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
    print("\n数据库迁移工具：完善 identified_stocks 表结构\n")
    
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
