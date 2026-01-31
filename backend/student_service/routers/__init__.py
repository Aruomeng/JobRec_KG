"""
学生服务路由模块
"""
from .recommend import router as recommend_router
from .user import router as user_router
from .jobs import router as jobs_router
from .favorites import router as favorites_router
from .common import router as common_router

__all__ = [
    "recommend_router",
    "user_router",
    "jobs_router",
    "favorites_router",
    "common_router"
]
