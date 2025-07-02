# setup_mssql.py
import pymssql
import os
from dotenv import load_dotenv

load_dotenv()

config = {
    "server": os.getenv("MSSQL_SERVER"),
    "user": os.getenv("MSSQL_USER"),
    "password": os.getenv("MSSQL_PASSWORD"),
    "database": os.getenv("MSSQL_DATABASE"),
    "charset": "utf8"
}

def setup_mssql():
    # 第一步：连接 master 数据库创建 notebook 库（如不存在）
    conn = pymssql.connect(
        server=config["server"],
        user=config["user"],
        password=config["password"],
        database="master",
        charset=config["charset"]
    )
    cursor = conn.cursor()
    cursor.execute("""
    IF NOT EXISTS (
        SELECT name FROM sys.databases WHERE name = %s
    )
    CREATE DATABASE [{}]
    """.format(config["database"]), (config["database"],))
    conn.commit()
    conn.close()

    # 第二步：连接 notebook 数据库，创建表及全文索引
    conn = pymssql.connect(**config)
    cursor = conn.cursor()

    # 创建表
    cursor.execute("""
    IF NOT EXISTS (
        SELECT * FROM sysobjects WHERE name='notes' AND xtype='U'
    )
    CREATE TABLE notes (
        id INT IDENTITY(1,1) PRIMARY KEY,
        content NVARCHAR(MAX),
        created_at DATETIME
    )
    """)
    conn.commit()

    # 创建全文目录（如果不存在）
    cursor.execute("""
    IF NOT EXISTS (
        SELECT * FROM sys.fulltext_catalogs WHERE name = 'ft_notes_catalog'
    )
    CREATE FULLTEXT CATALOG ft_notes_catalog AS DEFAULT
    """)
    conn.commit()

    # 获取主键索引名
    cursor.execute("""
    SELECT name FROM sys.indexes
    WHERE object_id = OBJECT_ID('notes') AND is_primary_key = 1
    """)
    index_name = cursor.fetchone()
    if not index_name:
        print("❌ 获取主键索引失败，无法继续。")
        return
    index_name = index_name[0]

    # 创建全文索引（如不存在）
    cursor.execute("""
    IF NOT EXISTS (
        SELECT * FROM sys.fulltext_indexes WHERE object_id = OBJECT_ID('notes')
    )
    CREATE FULLTEXT INDEX ON notes(content)
    KEY INDEX {} ON ft_notes_catalog
    """.format(index_name))
    conn.commit()

    print("✅ MSSQL 数据库与全文检索配置完成")
    conn.close()

if __name__ == "__main__":
    setup_mssql()
