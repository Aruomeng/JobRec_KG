"""
公共基础数据路由模块
"""
from fastapi import APIRouter
from ..dependencies import get_neo4j

router = APIRouter(tags=["common"])

neo4j_conn = get_neo4j()

@router.get("/api/common/cities")
def get_cities():
    """获取所有城市列表（按热门程度排序）"""
    query = """
    MATCH (c:City)
    OPTIONAL MATCH (c)<-[:LOCATED_IN]-(:Company)<-[:OFFERED_BY]-(j:Job)
    WITH c.name AS city, COUNT(j) AS job_count
    ORDER BY job_count DESC
    RETURN city, job_count
    """
    results = neo4j_conn.query(query)
    # 过滤掉空城市名
    return {"cities": [r["city"] for r in results if r["city"]]}
