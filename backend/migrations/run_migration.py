"""
执行数据库迁移 - 创建 favorites 表
"""
import psycopg2
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

DATABASE_URL = os.getenv("NEON_DATABASE_URL")

if not DATABASE_URL:
    print("错误: NEON_DATABASE_URL 未设置")
    exit(1)

# SQL 脚本
sql = """
CREATE TABLE IF NOT EXISTS favorites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id TEXT NOT NULL,
    job_title TEXT,
    company TEXT,
    salary TEXT,
    city TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, job_id)
);

CREATE INDEX IF NOT EXISTS idx_favorites_user_id ON favorites(user_id);
CREATE INDEX IF NOT EXISTS idx_favorites_job_id ON favorites(job_id);
"""

try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(sql)
    conn.commit()
    print("✅ favorites 表创建成功!")
    
    # 验证表结构
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'favorites'")
    columns = cur.fetchall()
    print("\n表结构:")
    for col in columns:
        print(f"  - {col[0]}: {col[1]}")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"❌ 错误: {e}")
