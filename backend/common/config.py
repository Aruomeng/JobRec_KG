"""
配置管理模块
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 确保加载backend目录下的.env文件
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Neo4j配置 (小写匹配.env)
NEO4J_URI = os.getenv("neo4j_uri", "bolt://localhost:7687")
NEO4J_USER = os.getenv("neo4j_user", "neo4j")
NEO4J_PASSWORD = os.getenv("neo4j_password", "TYH041113")

# Neon PostgreSQL配置
NEON_DATABASE_URL = os.getenv("NEON_DATABASE_URL", "")

# JWT配置 (小写匹配.env)
JWT_SECRET = os.getenv("jwt_secret_key", "zhitung-ai-job-rec-secret-key-2026")
JWT_ALGORITHM = os.getenv("algorithm", "HS256")
JWT_EXPIRE_HOURS = 24

# 服务端口配置
STUDENT_SERVICE_PORT = 8001
ENTERPRISE_SERVICE_PORT = 8002
UNIVERSITY_SERVICE_PORT = 8003
