"""
学生服务 - 工具函数
"""
import math
from datetime import datetime, timedelta
from typing import Optional, Any
from passlib.context import CryptContext

# 密码上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """获取密码哈希"""
    return pwd_context.hash(password)


def sanitize_data(data: Any) -> Any:
    """
    递归处理数据中的 NaN 值，将其转换为 None，以便 JSON 序列化。
    """
    if isinstance(data, dict):
        return {k: sanitize_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_data(item) for item in data]
    elif isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None
        return data
    return data
