"""
学生服务 - 依赖项
提供数据库连接、认证等共享依赖
"""
import sys
import psycopg2
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic_settings import BaseSettings

from common import config
from common.database import Neo4jConnection
from .models import TokenData

# 添加 GraphSAGE 推荐系统的路径
sys.path.insert(0, str(config.GRAPHSAGE_MODULE_PATH))


# ==================== 配置 ====================

class Settings(BaseSettings):
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    jwt_secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    neon_database_url: str = ""

    class Config:
        env_file = str(config.ENV_FILE_PATH)


# 初始化配置（单例）
settings = Settings()


# ==================== 数据库连接 ====================

# Neo4j 连接（使用增强的连接管理器）
neo4j_conn = Neo4jConnection()


def get_neo4j():
    """获取 Neo4j 连接"""
    return neo4j_conn


def get_neon_connection():
    """获取 Neon PostgreSQL 连接"""
    return psycopg2.connect(settings.neon_database_url)


# ==================== GraphSAGE 推荐器 ====================

graphsage_recommender = None

def init_graphsage():
    """初始化 GraphSAGE 推荐器"""
    global graphsage_recommender
    try:
        from hybrid_recommender import create_recommender_from_trained_model
        print("🔄 正在初始化GraphSAGE推荐器...")
        
        # 使用绝对路径
        model_path = str(config.GRAPHSAGE_MODEL_PATH)
        data_path = str(config.GRAPHSAGE_DATA_PATH)
        
        # print(f"   模型路径: {model_path}")
        # print(f"   数据路径: {data_path}")
        
        graphsage_recommender = create_recommender_from_trained_model(
            model_path=model_path,
            data_path=data_path,
            neo4j_uri=settings.neo4j_uri,
            neo4j_user=settings.neo4j_user,
            neo4j_password=settings.neo4j_password
        )
        print("✅ GraphSAGE推荐器初始化成功!")
    except Exception as e:
        print(f"❌ GraphSAGE推荐器初始化失败: {e}")
        import traceback
        traceback.print_exc()
        graphsage_recommender = None


def get_graphsage():
    """获取 GraphSAGE 推荐器"""
    return graphsage_recommender


# ==================== 认证 ====================

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    return token_data


# ==================== Neo4j 索引 ====================

def create_neo4j_indexes():
    """创建关键字段索引以优化查询性能"""
    index_queries = [
        "CREATE INDEX IF NOT EXISTS FOR (s:Student) ON (s.student_id)",
        "CREATE INDEX IF NOT EXISTS FOR (j:Job) ON (j.job_id)",
        "CREATE INDEX IF NOT EXISTS FOR (sk:Skill) ON (sk.name)",
        "CREATE INDEX IF NOT EXISTS FOR (c:Course) ON (c.name)",
        "CREATE INDEX IF NOT EXISTS FOR (j:Job) ON (j.city)",
        "CREATE INDEX IF NOT EXISTS FOR (j:Job) ON (j.title)",
    ]
    for idx_query in index_queries:
        try:
            neo4j_conn.query(idx_query)
        except Exception as e:
            print(f"索引创建警告: {e}")
    print("✅ Neo4j 索引创建/验证完成")
