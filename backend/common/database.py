"""
数据库连接模块 - 增强版
- 连接池管理
- 健康检查和自动重连
- 完善的异常处理
"""
import time
import logging
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from threading import Lock

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, SessionExpired, AuthError
from supabase import create_client, Client
from . import config

# 配置日志
logger = logging.getLogger(__name__)

# ==================== Neo4j 连接管理 ====================

class Neo4jConnectionManager:
    """
    Neo4j 连接管理器
    - 连接池由 Neo4j 驱动内置管理
    - 健康检查和自动重连
    - 线程安全的单例模式
    """
    
    _instance = None
    _lock = Lock()
    
    # 连接池配置
    MAX_CONNECTION_POOL_SIZE = 50
    CONNECTION_TIMEOUT = 30  # 秒
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY = 1  # 秒
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._driver = None
        self._last_health_check = 0
        self._health_check_interval = 60  # 每60秒检查一次
        self._initialized = True
        self._connect()
    
    def _connect(self) -> bool:
        """建立 Neo4j 连接"""
        try:
            if self._driver:
                self._driver.close()
            
            self._driver = GraphDatabase.driver(
                config.NEO4J_URI,
                auth=(config.NEO4J_USER, config.NEO4J_PASSWORD),
                max_connection_pool_size=self.MAX_CONNECTION_POOL_SIZE,
                connection_timeout=self.CONNECTION_TIMEOUT,
            )
            
            # 验证连接
            self._driver.verify_connectivity()
            logger.info(f"✅ Neo4j 连接成功: {config.NEO4J_URI}")
            return True
            
        except AuthError as e:
            logger.error(f"❌ Neo4j 认证失败: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Neo4j 连接失败: {e}")
            return False
    
    def _ensure_connection(self):
        """确保连接有效，必要时重连"""
        current_time = time.time()
        
        # 定期健康检查
        if current_time - self._last_health_check > self._health_check_interval:
            self._last_health_check = current_time
            if not self.health_check():
                self._reconnect()
    
    def _reconnect(self):
        """重连机制"""
        for attempt in range(self.MAX_RETRY_ATTEMPTS):
            logger.warning(f"🔄 尝试重连 Neo4j (第 {attempt + 1}/{self.MAX_RETRY_ATTEMPTS} 次)")
            if self._connect():
                return
            time.sleep(self.RETRY_DELAY * (attempt + 1))  # 指数退避
        
        logger.error("❌ Neo4j 重连失败，已达最大重试次数")
    
    def health_check(self) -> bool:
        """健康检查"""
        if not self._driver:
            return False
        
        try:
            self._driver.verify_connectivity()
            return True
        except Exception as e:
            logger.warning(f"⚠️ Neo4j 健康检查失败: {e}")
            return False
    
    def query(self, cypher: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """
        执行 Cypher 查询
        - 自动重试连接错误
        - 返回记录列表
        """
        self._ensure_connection()
        
        for attempt in range(self.MAX_RETRY_ATTEMPTS):
            try:
                with self._driver.session() as session:
                    result = session.run(cypher, parameters or {})
                    return [record.data() for record in result]
                    
            except (ServiceUnavailable, SessionExpired) as e:
                logger.warning(f"⚠️ Neo4j 连接异常 (尝试 {attempt + 1}): {e}")
                if attempt < self.MAX_RETRY_ATTEMPTS - 1:
                    self._reconnect()
                    time.sleep(self.RETRY_DELAY)
                else:
                    raise
                    
            except Exception as e:
                logger.error(f"❌ Neo4j 查询错误: {e}")
                raise
        
        return []
    
    def execute_write(self, cypher: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """执行写操作（与 query 相同，语义更明确）"""
        return self.query(cypher, parameters)
    
    @contextmanager
    def session(self):
        """获取原始 session（用于事务操作）"""
        self._ensure_connection()
        session = self._driver.session()
        try:
            yield session
        finally:
            session.close()
    
    def close(self):
        """关闭连接"""
        if self._driver:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j 连接已关闭")


# ==================== 全局连接实例 ====================

_neo4j_manager: Optional[Neo4jConnectionManager] = None

def get_neo4j_connection() -> Neo4jConnectionManager:
    """获取 Neo4j 连接管理器单例"""
    global _neo4j_manager
    if _neo4j_manager is None:
        _neo4j_manager = Neo4jConnectionManager()
    return _neo4j_manager


# 兼容旧代码的别名
def get_neo4j_driver():
    """兼容旧代码：返回连接管理器"""
    return get_neo4j_connection()


def close_neo4j():
    """关闭 Neo4j 连接"""
    global _neo4j_manager
    if _neo4j_manager:
        _neo4j_manager.close()
        _neo4j_manager = None


# ==================== Neo4j 兼容类 ====================

class Neo4jConnection:
    """
    兼容旧代码的 Neo4j 连接类
    实际委托给 Neo4jConnectionManager
    """
    
    def __init__(self, uri=None, user=None, password=None):
        """
        初始化（参数被忽略，使用全局配置）
        保留参数是为了兼容现有代码
        """
        self._manager = get_neo4j_connection()
    
    def query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """执行查询"""
        return self._manager.query(query, parameters)
    
    def close(self):
        """关闭连接（实际不关闭，由全局管理）"""
        pass  # 不真正关闭，避免服务中途断开
    
    def health_check(self) -> bool:
        """健康检查"""
        return self._manager.health_check()


# ==================== Supabase 连接 ====================

_supabase_client: Optional[Client] = None

def get_supabase_client() -> Optional[Client]:
    """获取 Supabase 客户端单例"""
    global _supabase_client
    if _supabase_client is None:
        if config.SUPABASE_URL and config.SUPABASE_KEY:
            _supabase_client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        else:
            logger.warning("⚠️ Supabase 配置未设置，部分功能不可用")
            return None
    return _supabase_client


def get_supabase_admin_client() -> Optional[Client]:
    """获取 Supabase 管理员客户端（使用 Service Key）"""
    if config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY:
        return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    return None
