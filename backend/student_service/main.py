"""
学生服务 - 主入口
精简版：所有业务逻辑已拆分到各模块
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 导入路由
from .routers import recommend_router, user_router, jobs_router, favorites_router
from .dependencies import create_neo4j_indexes, init_graphsage

# 创建 FastAPI 应用
app = FastAPI(
    title="高校就业推荐系统 - 学生服务",
    version="2.0.0",
    description="学生端 API，包含职位推荐、技能诊断、课程管理等功能"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应设置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(recommend_router)
app.include_router(user_router)
app.include_router(jobs_router)
app.include_router(favorites_router)


# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    # 创建 Neo4j 索引
    create_neo4j_indexes()
    # 初始化 GraphSAGE 推荐器
    init_graphsage()


# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理资源"""
    from .dependencies import get_neo4j
    neo4j_conn = get_neo4j()
    neo4j_conn.close()


# 根路由
@app.get("/")
def read_root():
    """API 根路由"""
    return {
        "service": "student-service",
        "version": "2.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("student_service.main:app", host="0.0.0.0", port=8001, reload=True)
