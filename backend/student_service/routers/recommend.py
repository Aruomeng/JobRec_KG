"""
学生服务 - 推荐相关路由
包含：热门职位、职位推荐、技能推荐、混合推荐
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, Dict

from ..models import (
    JobRecommendationRequest,
    SkillRecommendationRequest,
    HybridRecommendationRequest
)
from ..utils import sanitize_data
from ..dependencies import get_neo4j, get_graphsage

router = APIRouter(prefix="/api/student", tags=["recommend"])

# 获取依赖
neo4j_conn = get_neo4j()


@router.get("/hot-jobs")
def get_hot_jobs(limit: int = 20):
    """获取热门职位"""
    query = """
    MATCH (j:Job)
    WITH j
    ORDER BY j.view_count DESC LIMIT $limit
    OPTIONAL MATCH (j)-[:OFFERED_BY]->(cp:Company)
    OPTIONAL MATCH (cp)-[:LOCATED_IN]->(ct:City)
    OPTIONAL MATCH (j)-[:REQUIRES_SKILL]->(req_sk:Skill)
    RETURN j.url AS job_id, j.title AS title, j.salary AS salary, cp.name AS company, 
           HEAD(COLLECT(DISTINCT ct.name)) AS city, j.education AS education, 
           COLLECT(DISTINCT req_sk.name) AS required_skills
    """
    results = neo4j_conn.query(query, parameters={"limit": limit})
    return sanitize_data({"jobs": results})


@router.post("/recommend-jobs")
def recommend_jobs(request: JobRecommendationRequest):
    """基于学生技能推荐职位"""
    query = """
    MATCH (s:Student {student_id: $student_id})-[:HAS_SKILL]->(sk:Skill)<-[:REQUIRES_SKILL]-(j:Job)
    """
    parameters = {
        "student_id": request.student_id,
        "top_k": 200
    }

    if request.city:
        query += 'MATCH (j)-[:OFFERED_BY]->(:Company)-[:LOCATED_IN]->(:City {name: $city}) '
        parameters["city"] = request.city

    query += """
    WITH j, COUNT(sk) AS match_count
    ORDER BY match_count DESC LIMIT $top_k
    OPTIONAL MATCH (j)-[:OFFERED_BY]->(cp:Company)
    OPTIONAL MATCH (cp)-[:LOCATED_IN]->(ct:City)
    OPTIONAL MATCH (j)-[:REQUIRES_SKILL]->(req_sk:Skill)
    RETURN j.url AS job_id, j.title AS title, j.salary AS salary, cp.name AS company, 
           HEAD(COLLECT(DISTINCT ct.name)) AS city, j.education AS education, 
           COLLECT(DISTINCT req_sk.name) AS required_skills,
           match_count
    """
    results = neo4j_conn.query(query, parameters=parameters)
    
    for result in results:
        match_count = result.pop("match_count")
        required_skills = result.get("required_skills") or []
        total_skills = len(required_skills)
        result["match_rate"] = match_count / total_skills if total_skills > 0 else 0
        result["match_score"] = result["match_rate"]
    
    results = [r for r in results if r.get("match_rate", 0) >= 0.3]
    results.sort(key=lambda x: x.get("match_rate", 0), reverse=True)
    
    return sanitize_data({"recommendations": results})


@router.post("/recommend-by-skills")
def recommend_by_skills(request: SkillRecommendationRequest):
    """基于技能推荐逻辑，支持 KG 和 AI 两种模式"""
    if not request.skills:
        return {"recommendations": []}
    
    graphsage_recommender = get_graphsage()
    
    # AI 模式
    if request.use_model and graphsage_recommender:
        try:
            student_id = request.student_id or "anonymous"
            
            user_info_query = """
            MATCH (s:Student {student_id: $student_id})
            OPTIONAL MATCH (s)-[:ENROLLED_IN]->(c:Course)
            RETURN s.expected_position as expected_position, 
                   s.education as education,
                   collect(DISTINCT c.name) as courses
            """
            user_info_result = neo4j_conn.query(user_info_query, parameters={"student_id": student_id})
            
            expected_position = None
            education = None
            courses = []
            
            if user_info_result and user_info_result[0]:
                expected_position = user_info_result[0].get("expected_position")
                education = user_info_result[0].get("education")
                courses = user_info_result[0].get("courses", []) or []
            
            recommendations = graphsage_recommender.recommend_pure_dl(
                student_id=student_id,
                top_k=request.top_k,
                city=request.city,
                skills=request.skills,
                expected_position=expected_position,
                education=education,
                courses=courses
            )
            
            formatted_results = []
            for rec in recommendations:
                job_id = rec.job_id
                if '/' in job_id:
                    job_id = job_id.split('/')[-1]
                
                job_query = """
                MATCH (j:Job)
                WHERE j.url ENDS WITH $job_suffix OR j.url = $job_suffix
                OPTIONAL MATCH (j)-[:OFFERED_BY]->(cp:Company)
                OPTIONAL MATCH (cp)-[:LOCATED_IN]->(ct:City)
                OPTIONAL MATCH (j)-[:REQUIRES_SKILL]->(req_sk:Skill)
                RETURN j.url AS job_id, j.title AS title, j.salary AS salary, 
                       cp.name AS company, COLLECT(DISTINCT ct.name) AS cities, j.education AS education,
                       COLLECT(DISTINCT req_sk.name) AS required_skills
                LIMIT 1
                """
                job_details = neo4j_conn.query(job_query, parameters={"job_suffix": job_id})
                
                if job_details:
                    job_info = job_details[0]
                    cities = [c for c in (job_info.get("cities") or []) if c]
                    if cities:
                        if request.city and request.city in cities:
                            display_city = request.city
                        else:
                            display_city = cities[0]
                    else:
                        display_city = "不限"
                    formatted_results.append({
                        "job_id": job_info["job_id"],
                        "title": job_info["title"],
                        "salary": job_info["salary"],
                        "company": job_info["company"],
                        "city": display_city,
                        "education": job_info["education"],
                        "required_skills": job_info["required_skills"],
                        "matched_skills": rec.matched_skills,
                        "match_rate": rec.final_score,
                        "match_score": rec.final_score,
                        "deep_score": rec.deep_score,
                        "skill_score": rec.skill_score,
                        "rule_score": rec.rule_score,
                        "explanation": rec.explanation
                    })
            
            formatted_results.sort(key=lambda x: x.get("match_rate", 0), reverse=True)
            return sanitize_data({"recommendations": formatted_results, "algorithm": "Deep Learning (GraphSAGE)"})
        except Exception as e:
            print(f"GraphSAGE 推荐失败, 回退到 KG 模式: {e}")
    
    # KG 模式
    if request.city:
        query = """
        UNWIND $skills AS skill_name
        MATCH (sk:Skill {name: skill_name})<-[:REQUIRES_SKILL]-(j:Job)
        MATCH (j)-[:OFFERED_BY]->(comp:Company)-[:LOCATED_IN]->(ct:City {name: $city})
        WITH j, comp, ct, COLLECT(DISTINCT sk.name) AS matched_skills
        ORDER BY SIZE(matched_skills) DESC LIMIT $top_k
        OPTIONAL MATCH (j)-[:REQUIRES_SKILL]->(req_sk:Skill)
        RETURN j.url AS job_id, j.title AS title, j.salary AS salary, comp.name AS company, 
               ct.name AS city, j.education AS education, 
               COLLECT(DISTINCT req_sk.name) AS required_skills,
               matched_skills
        """
        parameters = {"skills": request.skills, "top_k": request.top_k, "city": request.city}
    else:
        query = """
        UNWIND $skills AS skill_name
        MATCH (sk:Skill {name: skill_name})<-[:REQUIRES_SKILL]-(j:Job)
        WITH j, COLLECT(DISTINCT sk.name) AS matched_skills
        ORDER BY SIZE(matched_skills) DESC LIMIT $top_k
        OPTIONAL MATCH (j)-[:OFFERED_BY]->(cp:Company)
        OPTIONAL MATCH (cp)-[:LOCATED_IN]->(ct:City)
        OPTIONAL MATCH (j)-[:REQUIRES_SKILL]->(req_sk:Skill)
        RETURN j.url AS job_id, j.title AS title, j.salary AS salary, cp.name AS company, 
               HEAD(COLLECT(DISTINCT ct.name)) AS city, j.education AS education, 
               COLLECT(DISTINCT req_sk.name) AS required_skills,
               matched_skills
        """
        parameters = {"skills": request.skills, "top_k": request.top_k}
    
    results = neo4j_conn.query(query, parameters=parameters)
    
    expected_position = None
    if request.student_id:
        user_query = "MATCH (s:Student {student_id: $sid}) RETURN s.expected_position as pos"
        user_result = neo4j_conn.query(user_query, parameters={"sid": request.student_id})
        if user_result and user_result[0]:
            expected_position = user_result[0].get("pos")
    
    for result in results:
        matched_skills = result.get("matched_skills", [])
        required_skills = result.get("required_skills") or []
        total_skills = len(required_skills)
        skill_match_rate = len(matched_skills) / total_skills if total_skills > 0 else 0
        
        position_boost = 1.0
        job_title = result.get("title", "").lower() if result.get("title") else ""
        if expected_position and job_title:
            expected_lower = expected_position.lower()
            if expected_lower in job_title or job_title in expected_lower:
                position_boost = 1.15
            else:
                keywords = expected_lower.split()
                match_count = sum(1 for kw in keywords if kw in job_title)
                if match_count > 0:
                    position_boost = 1.0 + 0.05 * (match_count / len(keywords))
        
        result["match_rate"] = skill_match_rate * position_boost
        result["match_score"] = result["match_rate"]
        result["position_match"] = position_boost > 1.0
        result["skill_coverage"] = f"{len(matched_skills)}/{total_skills}"
    
    results = [r for r in results if r.get("match_rate", 0) >= 0.3]
    results.sort(key=lambda x: x.get("match_rate", 0), reverse=True)
    
    return sanitize_data({"recommendations": results, "algorithm": "Knowledge Graph Based"})


@router.post("/hybrid-recommend")
def hybrid_recommend(request: HybridRecommendationRequest):
    """混合推荐（GraphSAGE + 知识图谱）"""
    graphsage_recommender = get_graphsage()
    
    if not graphsage_recommender:
        raise HTTPException(status_code=503, detail="GraphSAGE推荐器服务不可用")
    
    try:
        weights = request.weights
        if weights:
            weight_tuple = (weights.get('deep', 0.6), weights.get('skill', 0.3), weights.get('rule', 0.1))
        else:
            weight_tuple = (0.6, 0.3, 0.1)
        
        skills_query = """
        MATCH (s:Student {student_id: $student_id})-[:HAS_SKILL]->(sk:Skill)
        RETURN collect(sk.name) as skills
        """
        skills_result = neo4j_conn.query(skills_query, parameters={"student_id": request.student_id})
        student_skills = skills_result[0]["skills"] if skills_result and skills_result[0]["skills"] else []
        
        recommendations = graphsage_recommender.recommend(
            student_id=request.student_id,
            recall_k=request.recall_k,
            rank_k=request.rank_k,
            final_k=request.final_k,
            weights=weight_tuple,
            city=request.city,
            skills=student_skills
        )
        
        formatted_results = []
        for rec in recommendations:
            job_id = rec.job_id
            if '/' in job_id:
                job_id = job_id.split('/')[-1]
            
            job_query = """
            MATCH (j:Job)
            WHERE j.url ENDS WITH $job_suffix OR j.url = $job_suffix
            OPTIONAL MATCH (j)-[:OFFERED_BY]->(cp:Company)
            OPTIONAL MATCH (cp)-[:LOCATED_IN]->(ct:City)
            OPTIONAL MATCH (j)-[:REQUIRES_SKILL]->(req_sk:Skill)
            RETURN j.url AS job_id, j.title AS title, j.salary AS salary, 
                   cp.name AS company, HEAD(COLLECT(DISTINCT ct.name)) AS city, j.education AS education,
                   j.experience AS experience,
                   COLLECT(DISTINCT req_sk.name) AS required_skills, j.description AS description
            LIMIT 1
            """
            
            job_details = neo4j_conn.query(job_query, parameters={"job_suffix": job_id})
            
            if job_details:
                job_info = job_details[0]
                
                insight = None
                if request.include_insight:
                    direct_skill_query = """
                    MATCH (s:Student {student_id: $student_id})-[:HAS_SKILL]->(sk:Skill)
                          <-[:REQUIRES_SKILL]-(j:Job)
                    WHERE j.url ENDS WITH $job_suffix
                    RETURN sk.name AS skill
                    """
                    direct_results = neo4j_conn.query(direct_skill_query, parameters={
                        "student_id": request.student_id,
                        "job_suffix": job_id
                    })
                    direct_skills = set(r["skill"] for r in direct_results) if direct_results else set()
                    
                    course_skill_query = """
                    MATCH (s:Student {student_id: $student_id})-[:TAKES]->(c:Course)-[:TEACHES_SKILL]->(sk:Skill)
                          <-[:REQUIRES_SKILL]-(j:Job)
                    WHERE j.url ENDS WITH $job_suffix
                    RETURN sk.name AS skill, COLLECT(DISTINCT c.name) AS sources
                    """
                    course_results = neo4j_conn.query(course_skill_query, parameters={
                        "student_id": request.student_id,
                        "job_suffix": job_id
                    })
                    
                    skill_paths = []
                    for skill in direct_skills:
                        skill_paths.append({"skill": skill, "sources": [], "direct_match": True})
                    
                    if course_results:
                        for r in course_results:
                            if r["skill"] not in direct_skills:
                                skill_paths.append({
                                    "skill": r["skill"],
                                    "sources": r["sources"],
                                    "direct_match": False
                                })
                    
                    if skill_paths:
                        insight = {"skill_paths": skill_paths}
                
                formatted_results.append({
                    "job_id": job_info["job_id"],
                    "title": job_info["title"],
                    "salary": job_info["salary"],
                    "company": job_info["company"],
                    "city": request.city if request.city else job_info["city"],
                    "education": job_info["education"],
                    "experience": job_info.get("experience"),
                    "required_skills": job_info["required_skills"],
                    "match_rate": rec.final_score,
                    "match_score": rec.final_score,
                    "matched_skills": rec.matched_skills,
                    "deep_score": rec.deep_score,
                    "skill_score": rec.skill_score,
                    "rule_score": rec.rule_score,
                    "explanation": rec.explanation,
                    "insight": insight
                })
        
        formatted_results = [r for r in formatted_results if r.get("match_rate", 0) >= 0.3]
        
        return sanitize_data({"recommendations": formatted_results})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推荐失败: {str(e)}")
