"""
数据库连接模块
"""
from neo4j import GraphDatabase
from supabase import create_client, Client
from typing import Optional
from . import config

# Neo4j驱动实例
_neo4j_driver = None

def get_neo4j_driver():
    """获取Neo4j驱动单例"""
    global _neo4j_driver
    if _neo4j_driver is None:
        _neo4j_driver = GraphDatabase.driver(
            config.NEO4J_URI,
            auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
        )
    return _neo4j_driver

def close_neo4j():
    """关闭Neo4j连接"""
    global _neo4j_driver
    if _neo4j_driver:
        _neo4j_driver.close()
        _neo4j_driver = None

# Supabase客户端实例
_supabase_client: Optional[Client] = None

def get_supabase_client() -> Optional[Client]:
    """获取Supabase客户端单例"""
    global _supabase_client
    if _supabase_client is None:
        if config.SUPABASE_URL and config.SUPABASE_KEY:
            _supabase_client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        else:
            print("警告: Supabase配置未设置，认证功能不可用")
            return None
    return _supabase_client

def get_supabase_admin_client() -> Optional[Client]:
    """获取Supabase管理员客户端（使用Service Key）"""
    if config.SUPABASE_URL and config.SUPABASE_SERVICE_KEY:
        return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    return None
