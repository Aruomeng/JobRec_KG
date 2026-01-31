"""
学生服务 - 职位相关路由
包含：职位详情、职位知识图谱、城市列表
"""
from fastapi import APIRouter, HTTPException, Body
from typing import Optional, Dict

from ..utils import sanitize_data
from ..dependencies import get_neo4j

router = APIRouter(tags=["jobs"])

neo4j_conn = get_neo4j()


@router.get("/api/job/detail/{job_id:path}")
def get_job_detail(job_id: str):
    """获取职位详情"""
    query = """
    MATCH (j:Job {url: $job_id})
    OPTIONAL MATCH (j)-[:OFFERED_BY]->(cp:Company)
    OPTIONAL MATCH (cp)-[:LOCATED_IN]->(ct:City)
    OPTIONAL MATCH (j)-[:BELONGS_TO_INDUSTRY]->(ind:Industry)
    OPTIONAL MATCH (j)-[:REQUIRES_SKILL]->(req_sk:Skill)
    RETURN j.url AS job_id, j.title AS title, j.salary AS salary, cp.name AS company, 
           COLLECT(DISTINCT ct.name) AS cities, j.education AS education, 
           j.experience AS experience,
           HEAD(COLLECT(DISTINCT ind.name)) AS industry,
           COLLECT(DISTINCT req_sk.name) AS required_skills, 
           j.description AS description
    """
    
    results = neo4j_conn.query(query, parameters={"job_id": job_id})
    
    if not results:
        raise HTTPException(status_code=404, detail="Job not found")
    
    result = results[0]
    cities = [c for c in (result.get("cities") or []) if c]
    result["city"] = cities[0] if cities else "不限"
    result["cities"] = cities
    
    return sanitize_data(result)


@router.post("/api/job/{job_id:path}/graph")
def get_job_graph(job_id: str, request_body: Optional[Dict] = Body(default=None)):
    """获取职位知识图谱"""
    user_skills = request_body.get("user_skills", []) if request_body else []
    
    query = """
    MATCH (j:Job {url: $job_id})-[:REQUIRES_SKILL]->(sk:Skill)
    OPTIONAL MATCH (sk)<-[:TEACHES_SKILL]-(c:Course)
    RETURN sk.name AS skill, COLLECT(DISTINCT c.name) AS courses
    """
    
    results = neo4j_conn.query(query, parameters={"job_id": job_id})
    
    context_query = """
    MATCH (j:Job {url: $job_id})
    OPTIONAL MATCH (j)-[:OFFERED_BY]->(cp:Company)
    OPTIONAL MATCH (cp)-[:LOCATED_IN]->(ct:City)
    OPTIONAL MATCH (j)-[:BELONGS_TO_INDUSTRY]->(ind:Industry)
    RETURN j.title AS title, cp.name AS company, COLLECT(DISTINCT ct.name) AS cities, ind.name AS industry
    """
    context_results = neo4j_conn.query(context_query, parameters={"job_id": job_id})
    
    if context_results:
        raw_info = context_results[0]
        cities = [c for c in (raw_info.get("cities") or []) if c]
        display_city = request_body.get("display_city") if request_body else None
        job_info = {
            "title": raw_info.get("title", "Unknown Job"),
            "company": raw_info.get("company"),
            "city": display_city or (cities[0] if cities else None),
            "industry": raw_info.get("industry")
        }
    else:
        job_info = {"title": "Unknown Job", "company": None, "city": None, "industry": None}

    nodes = [{
        "id": "job",
        "label": "Job",
        "name": job_info["title"]
    }]
    
    edges = []
    
    if job_info["city"]:
        nodes.append({"id": "city", "label": "City", "name": job_info["city"]})
        edges.append({"source": "job", "target": "city", "type": "LOCATED_IN"})
    
    if job_info["industry"]:
        nodes.append({"id": "industry", "label": "Industry", "name": job_info["industry"]})
        edges.append({"source": "job", "target": "industry", "type": "BELONGS_TO"})

    def skill_fuzzy_match(required_skill: str, user_skills: list) -> bool:
        """技能模糊匹配"""
        if not user_skills:
            return False
        
        required_lower = required_skill.lower()
        
        for user_skill in user_skills:
            user_lower = user_skill.lower()
            if required_lower == user_lower:
                return True
            if required_lower in user_lower:
                return True
            if user_lower in required_lower:
                return True
        
        return False
    
    for result in results:
        skill = result["skill"]
        nodes.append({
            "id": skill,
            "label": "Skill",
            "name": skill,
            "matched": skill_fuzzy_match(skill, user_skills)
        })
        
        edges.append({
            "source": "job",
            "target": skill,
            "type": "REQUIRES"
        })
        
        for course in result["courses"]:
            course_id = f"course_{course}"
            nodes.append({
                "id": course_id,
                "label": "Course",
                "name": course
            })
            
            edges.append({
                "source": course_id,
                "target": skill,
                "type": "TEACHES"
            })
    
    return sanitize_data({"nodes": nodes, "edges": edges})


@router.get("/api/student/cities")
def get_cities():
    """获取城市列表"""
    query = """
    MATCH (c:City)
    OPTIONAL MATCH (c)<-[:LOCATED_IN]-(:Company)<-[:OFFERED_BY]-(j:Job)
    WITH c.name AS city, COUNT(j) AS job_count
    ORDER BY job_count DESC
    RETURN city
    """
    results = neo4j_conn.query(query)
    return {"cities": [r["city"] for r in results if r["city"]]}


@router.get("/api/student/health")
def health_check():
    """健康检查"""
    return {"status": "ok"}
