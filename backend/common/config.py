"""
配置管理模块
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# ==================== 路径配置 ====================
# backend/ 目录
BACKEND_DIR = Path(__file__).parent.parent.resolve()

# 项目根目录 (jobrec/)
PROJECT_ROOT = BACKEND_DIR.parent

# GraphSAGE 推荐系统路径
GRAPHSAGE_MODULE_PATH = PROJECT_ROOT / "模块_推荐系统" / "深度学习GraphSAGE" / "源代码" / "核心模块"
GRAPHSAGE_MODEL_PATH = GRAPHSAGE_MODULE_PATH / "输出" / "模型权重" / "graphsage_model.pth"
GRAPHSAGE_DATA_PATH = GRAPHSAGE_MODULE_PATH / "graph_data.pt"

# .env 文件路径
ENV_FILE_PATH = BACKEND_DIR / ".env"

# ==================== 加载环境变量 ====================
load_dotenv(ENV_FILE_PATH)

# ==================== Neo4j 配置 ====================
NEO4J_URI = os.getenv("neo4j_uri", "bolt://localhost:7687")
NEO4J_USER = os.getenv("neo4j_user", "neo4j")
NEO4J_PASSWORD = os.getenv("neo4j_password", "TYH041113")

# ==================== Neon PostgreSQL 配置 ====================
NEON_DATABASE_URL = os.getenv("NEON_DATABASE_URL", "")

# ==================== JWT 配置 ====================
JWT_SECRET = os.getenv("jwt_secret_key", "zhitung-ai-job-rec-secret-key-2026")
JWT_ALGORITHM = os.getenv("algorithm", "HS256")
JWT_EXPIRE_HOURS = 24

# ==================== 服务端口配置 ====================
STUDENT_SERVICE_PORT = 8001
ENTERPRISE_SERVICE_PORT = 8002
UNIVERSITY_SERVICE_PORT = 8003
