"""
企业端后端服务
端口: 8002
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings
from pydantic import BaseModel
from neo4j import GraphDatabase
from typing import List, Optional
from passlib.context import CryptContext
import psycopg2
import math
import os
import sys

# 导入统一配置
from common import config

# 添加GraphSAGE推荐系统的路径 (使用配置)
sys.path.insert(0, str(config.GRAPHSAGE_MODULE_PATH))

# 配置类
class Settings(BaseSettings):
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    jwt_secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    neon_database_url: str = ""
    
    class Config:
        env_file = str(config.ENV_FILE_PATH)

# 初始化配置
settings = Settings()

# 密码上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 导入共享的 Neo4j 连接（已包含连接池、健康检查和重连机制）
from common.database import Neo4jConnection

# 创建Neo4j连接实例
neo4j_conn = Neo4jConnection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

# Neon数据库连接
def get_neon_connection():
    return psycopg2.connect(settings.neon_database_url)

# 创建FastAPI应用
app = FastAPI(title="企业端API", version="2.0.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求模型
class LoginRequest(BaseModel):
    username: str
    password: str

class ScoutTalentsRequest(BaseModel):
    job_id: str
    top_k: int = 20
    education_filter: Optional[str] = None

class ResumeXRayRequest(BaseModel):
    student_id: str
    job_id: str

# =========== 企业个人中心 - 数据模型 ===========

class EnterpriseProfileUpdate(BaseModel):
    """企业资料更新请求"""
    company_name: Optional[str] = None
    industry: Optional[str] = None
    company_scale: Optional[str] = None
    city: Optional[str] = None
    contact_info: Optional[str] = None
    description: Optional[str] = None

class JobCreate(BaseModel):
    """职位创建请求"""
    title: str
    description: str
    education: str = "不限"
    experience: str = "不限"
    salary_min: int = 0
    salary_max: int = 0
    skills: List[str] = []
    city: Optional[str] = None

class JobUpdate(BaseModel):
    """职位更新请求"""
    title: Optional[str] = None
    description: Optional[str] = None
    education: Optional[str] = None
    experience: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    skills: Optional[List[str]] = None
    city: Optional[str] = None
    status: Optional[str] = None  # active/inactive

# 工具函数
def sanitize_data(data):
    if isinstance(data, dict):
        return {k: sanitize_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_data(v) for v in data]
    elif isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None
        return data
    return data

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# ==================== 企业端API ====================

@app.get("/api/")
def read_root():
    return {"message": "企业端API"}

# 企业端登录API
@app.post("/api/enterprise/login")
def enterprise_login(request: LoginRequest):
    """企业端登录（使用Neon数据库）"""
    try:
        conn = get_neon_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, username, password_hash, display_name, role 
            FROM users 
            WHERE username = %s AND role = 'enterprise'
        """, (request.username,))
        
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if not user:
            raise HTTPException(status_code=401, detail="用户不存在或非企业账号")
        
        user_id, username, password_hash, display_name, role = user
        
        if not verify_password(request.password, password_hash):
            raise HTTPException(status_code=401, detail="密码错误")
        
        return {
            "code": 200,
            "data": {
                "user_id": str(user_id),
                "username": username,
                "display_name": display_name,
                "role": role
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")

@app.post("/api/enterprise/scout-talents")
def scout_talents(request: ScoutTalentsRequest):
    """人才召回：根据职位要求找到匹配的学生"""
    job_id = request.job_id
    print(f"DEBUG scout-talents: job_id={job_id}")
    
    # 获取职位所需技能
    job_skills_query = """
    MATCH (j:Job)-[:REQUIRES_SKILL]->(sk:Skill)
    WHERE j.url ENDS WITH $job_suffix OR j.url = $job_id OR j.title CONTAINS $job_id
    RETURN COLLECT(DISTINCT sk.name) AS skills
    """
    job_result = neo4j_conn.query(job_skills_query, parameters={
        "job_id": job_id,
        "job_suffix": job_id.split('/')[-1] if '/' in job_id else job_id
    })
    job_skills = job_result[0]["skills"] if job_result and job_result[0]["skills"] else []
    
    # 如果没有通过职位找到技能，尝试将输入作为技能关键词直接搜索
    if not job_skills:
        skill_check_query = """
        MATCH (sk:Skill)
        WHERE sk.name CONTAINS $keyword OR toLower(sk.name) CONTAINS toLower($keyword)
        RETURN COLLECT(sk.name) AS skills
        LIMIT 20
        """
        skill_result = neo4j_conn.query(skill_check_query, parameters={"keyword": job_id})
        job_skills = skill_result[0]["skills"] if skill_result and skill_result[0]["skills"] else []
    
    if not job_skills:
        return {"candidates": []}
    
    # 查找匹配的学生
    simple_query = """
    MATCH (s:Student)
    OPTIONAL MATCH (s)-[:MAJORS_IN]->(major:Major)
    OPTIONAL MATCH (s)-[:HAS_SKILL]->(sk1:Skill) WHERE sk1.name IN $job_skills
    OPTIONAL MATCH (s)-[:TAKES|ENROLLED_IN]->(c:Course)-[:TEACHES_SKILL]->(sk2:Skill) WHERE sk2.name IN $job_skills
    OPTIONAL MATCH (s)-[:MAJORS_IN]->(:Major)-[:HAS_COURSE]->(c2:Course)-[:TEACHES_SKILL]->(sk3:Skill) WHERE sk3.name IN $job_skills
    WITH s, major, COLLECT(DISTINCT sk1.name) + COLLECT(DISTINCT sk2.name) + COLLECT(DISTINCT sk3.name) AS all_skills
    WITH s, major, [x IN all_skills WHERE x IS NOT NULL | x] AS matched_skills
    WHERE SIZE(matched_skills) > 0
    RETURN s.student_id AS student_id, s.name AS name, s.education AS education, 
           COALESCE(major.name, s.major) AS major, matched_skills, SIZE(matched_skills) AS match_count
    ORDER BY match_count DESC LIMIT $top_k
    """
    results = neo4j_conn.query(simple_query, parameters={
        "job_skills": job_skills,
        "top_k": request.top_k
    })
    
    # 格式化返回数据
    candidates = []
    for r in results:
        matched = list(set(r["matched_skills"])) if r["matched_skills"] else []
        match_score = len(matched) / len(job_skills) if job_skills else 0
        candidates.append({
            "student_id": r["student_id"],
            "name": r["name"] or "未知",
            "education": r["education"] or "未知",
            "major": r["major"] or "未知",
            "match_score": match_score,
            "matched_skills": matched
        })
    
    # 学历筛选
    if request.education_filter:
        candidates = [c for c in candidates if c["education"] == request.education_filter]
    
    return {"candidates": candidates}

@app.post("/api/enterprise/resume-xray")
def xray_resume(request: ResumeXRayRequest):
    """简历透视：分析学生与职位的技能匹配"""
    job_id = request.job_id
    job_suffix = job_id.split('/')[-1] if '/' in job_id else job_id
    
    # 获取学生技能
    student_query = """
    MATCH (s:Student {student_id: $student_id})-[:HAS_SKILL]->(sk:Skill)
    RETURN COLLECT(sk.name) AS skills
    """
    student_result = neo4j_conn.query(student_query, parameters={"student_id": request.student_id})
    student_skills = student_result[0]["skills"] if student_result else []
    
    # 获取职位技能
    job_query = """
    MATCH (j:Job)-[:REQUIRES_SKILL]->(sk:Skill)
    WHERE j.url ENDS WITH $job_suffix OR j.url = $job_id
    RETURN COLLECT(sk.name) AS skills
    """
    job_result = neo4j_conn.query(job_query, parameters={"job_id": job_id, "job_suffix": job_suffix})
    job_skills = job_result[0]["skills"] if job_result else []
    
    # 计算匹配
    matched_skills = [s for s in job_skills if s in student_skills]
    missing_skills = [s for s in job_skills if s not in student_skills]
    match_rate = len(matched_skills) / len(job_skills) if job_skills else 0
    
    return {
        "student_skills": student_skills,
        "job_skills": job_skills,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "match_rate": match_rate
    }

# ==================== 企业个人中心API ====================

@app.get("/api/enterprise/profile")
def get_enterprise_profile(user_id: str):
    """获取企业资料"""
    try:
        conn = get_neon_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, username, display_name, company_name, industry, 
                   company_scale, city, contact_info, description
            FROM users 
            WHERE id = %s AND role = 'enterprise'
        """, (user_id,))
        
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if not user:
            raise HTTPException(status_code=404, detail="企业用户不存在")
        
        return {
            "code": 200,
            "data": {
                "user_id": str(user[0]),
                "username": user[1],
                "display_name": user[2],
                "company_name": user[3] or "",
                "industry": user[4] or "",
                "company_scale": user[5] or "",
                "city": user[6] or "",
                "contact_info": user[7] or "",
                "description": user[8] or ""
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取资料失败: {str(e)}")

@app.put("/api/enterprise/profile")
def update_enterprise_profile(user_id: str, request: EnterpriseProfileUpdate):
    """更新企业资料"""
    try:
        conn = get_neon_connection()
        cur = conn.cursor()
        
        # 构建动态更新语句
        updates = []
        params = []
        
        if request.company_name is not None:
            updates.append("company_name = %s")
            params.append(request.company_name)
        if request.industry is not None:
            updates.append("industry = %s")
            params.append(request.industry)
        if request.company_scale is not None:
            updates.append("company_scale = %s")
            params.append(request.company_scale)
        if request.city is not None:
            updates.append("city = %s")
            params.append(request.city)
        if request.contact_info is not None:
            updates.append("contact_info = %s")
            params.append(request.contact_info)
        if request.description is not None:
            updates.append("description = %s")
            params.append(request.description)
        
        if updates:
            updates.append("updated_at = NOW()")
            params.append(user_id)
            
            sql = f"UPDATE users SET {', '.join(updates)} WHERE id = %s AND role = 'enterprise'"
            cur.execute(sql, params)
            conn.commit()
        
        # 如果提供了公司名，同步到Neo4j的Company节点
        if request.company_name:
            neo4j_conn.query("""
                MERGE (c:Company {name: $name})
                SET c.scale = $scale,
                    c.updated_at = datetime()
            """, {
                "name": request.company_name,
                "scale": request.company_scale or ""
            })
            
            # 如果有城市，建立LOCATED_IN关系
            if request.city:
                neo4j_conn.query("""
                    MERGE (city:City {name: $city})
                """, {"city": request.city})
                
                neo4j_conn.query("""
                    MATCH (c:Company {name: $company})
                    MATCH (city:City {name: $city})
                    MERGE (c)-[:LOCATED_IN]->(city)
                """, {"company": request.company_name, "city": request.city})
            
            # 如果有行业，建立关系
            if request.industry:
                neo4j_conn.query("""
                    MERGE (i:Industry {name: $industry})
                """, {"industry": request.industry})
        
        cur.close()
        conn.close()
        
        return {"code": 200, "message": "资料更新成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新资料失败: {str(e)}")

@app.post("/api/enterprise/jobs")
def create_job(user_id: str, request: JobCreate):
    """发布职位 - 创建Neo4j Job节点和关系"""
    try:
        # 先获取企业信息
        conn = get_neon_connection()
        cur = conn.cursor()
        cur.execute("SELECT company_name, city FROM users WHERE id = %s", (user_id,))
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if not result or not result[0]:
            raise HTTPException(status_code=400, detail="请先完善企业资料(设置公司名称)")
        
        company_name = result[0]
        company_city = result[1] or request.city
        
        # 生成唯一的职位URL作为ID
        import uuid
        import time
        job_url = f"enterprise_{user_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # 在Neo4j中创建Job节点
        neo4j_conn.query("""
            MERGE (j:Job {url: $url})
            SET j.title = $title,
                j.description = $description,
                j.education = $education,
                j.experience = $experience,
                j.salary_min = $salary_min,
                j.salary_max = $salary_max,
                j.salary = $salary_text,
                j.created_by = $user_id,
                j.created_at = datetime(),
                j.status = 'active'
        """, {
            "url": job_url,
            "title": request.title,
            "description": request.description,
            "education": request.education,
            "experience": request.experience,
            "salary_min": request.salary_min,
            "salary_max": request.salary_max,
            "salary_text": f"{request.salary_min}-{request.salary_max}K" if request.salary_max > 0 else "面议",
            "user_id": user_id
        })
        
        # 建立 OFFERED_BY 关系
        neo4j_conn.query("""
            MATCH (j:Job {url: $url})
            MATCH (c:Company {name: $company})
            MERGE (j)-[:OFFERED_BY]->(c)
        """, {"url": job_url, "company": company_name})
        
        # 建立 REQUIRES_SKILL 关系
        for skill in request.skills:
            skill = skill.strip()
            if skill:
                neo4j_conn.query("MERGE (s:Skill {name: $name})", {"name": skill})
                neo4j_conn.query("""
                    MATCH (j:Job {url: $url})
                    MATCH (s:Skill {name: $skill})
                    MERGE (j)-[:REQUIRES_SKILL]->(s)
                """, {"url": job_url, "skill": skill})
        
        # 如果有城市，建立关系
        if company_city:
            neo4j_conn.query("""
                MATCH (j:Job {url: $url})
                MATCH (c:Company)-[:LOCATED_IN]->(city:City)
                WHERE c.name = $company
                MERGE (j)-[:LOCATED_IN]->(city)
            """, {"url": job_url, "company": company_name})
        
        return {
            "code": 200,
            "message": "职位发布成功",
            "data": {"job_id": job_url}
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发布职位失败: {str(e)}")

@app.get("/api/enterprise/jobs")
def list_jobs(user_id: str):
    """获取企业发布的职位列表"""
    try:
        result = neo4j_conn.query("""
            MATCH (j:Job)
            WHERE j.created_by = $user_id
            OPTIONAL MATCH (j)-[:OFFERED_BY]->(c:Company)
            OPTIONAL MATCH (j)-[:REQUIRES_SKILL]->(s:Skill)
            RETURN j.url as job_id, j.title as title, j.description as description,
                   j.education as education, j.experience as experience,
                   j.salary_min as salary_min, j.salary_max as salary_max,
                   j.salary as salary, j.status as status, j.created_at as created_at,
                   c.name as company_name, collect(s.name) as skills
            ORDER BY j.created_at DESC
        """, {"user_id": user_id})
        
        jobs = []
        for record in result:
            jobs.append({
                "job_id": record["job_id"],
                "title": record["title"],
                "description": record["description"] or "",
                "education": record["education"] or "不限",
                "experience": record["experience"] or "不限",
                "salary_min": record["salary_min"] or 0,
                "salary_max": record["salary_max"] or 0,
                "salary": record["salary"] or "面议",
                "status": record["status"] or "active",
                "created_at": str(record["created_at"]) if record["created_at"] else "",
                "company_name": record["company_name"] or "",
                "skills": [s for s in record["skills"] if s]
            })
        
        return {"code": 200, "data": jobs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取职位列表失败: {str(e)}")

@app.put("/api/enterprise/jobs/{job_id}")
def update_job(job_id: str, request: JobUpdate):
    """更新职位信息"""
    try:
        # 构建更新语句
        updates = []
        params = {"url": job_id}
        
        if request.title is not None:
            updates.append("j.title = $title")
            params["title"] = request.title
        if request.description is not None:
            updates.append("j.description = $description")
            params["description"] = request.description
        if request.education is not None:
            updates.append("j.education = $education")
            params["education"] = request.education
        if request.experience is not None:
            updates.append("j.experience = $experience")
            params["experience"] = request.experience
        if request.salary_min is not None:
            updates.append("j.salary_min = $salary_min")
            params["salary_min"] = request.salary_min
        if request.salary_max is not None:
            updates.append("j.salary_max = $salary_max")
            params["salary_max"] = request.salary_max
        if request.salary_min is not None and request.salary_max is not None:
            updates.append("j.salary = $salary_text")
            params["salary_text"] = f"{request.salary_min}-{request.salary_max}K" if request.salary_max > 0 else "面议"
        if request.status is not None:
            updates.append("j.status = $status")
            params["status"] = request.status
        
        if updates:
            updates.append("j.updated_at = datetime()")
            query = f"MATCH (j:Job {{url: $url}}) SET {', '.join(updates)}"
            neo4j_conn.query(query, params)
        
        # 更新技能关系
        if request.skills is not None:
            # 删除旧的技能关系
            neo4j_conn.query("""
                MATCH (j:Job {url: $url})-[r:REQUIRES_SKILL]->()
                DELETE r
            """, {"url": job_id})
            
            # 建立新的技能关系
            for skill in request.skills:
                skill = skill.strip()
                if skill:
                    neo4j_conn.query("MERGE (s:Skill {name: $name})", {"name": skill})
                    neo4j_conn.query("""
                        MATCH (j:Job {url: $url})
                        MATCH (s:Skill {name: $skill})
                        MERGE (j)-[:REQUIRES_SKILL]->(s)
                    """, {"url": job_id, "skill": skill})
        
        return {"code": 200, "message": "职位更新成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新职位失败: {str(e)}")

@app.delete("/api/enterprise/jobs/{job_id}")
def delete_job(job_id: str, user_id: str):
    """删除职位"""
    try:
        # 验证是否是该用户创建的职位
        result = neo4j_conn.query("""
            MATCH (j:Job {url: $url})
            RETURN j.created_by as created_by
        """, {"url": job_id})
        
        if not result:
            raise HTTPException(status_code=404, detail="职位不存在")
        
        if result[0]["created_by"] != user_id:
            raise HTTPException(status_code=403, detail="无权删除此职位")
        
        # 删除职位及其关系
        neo4j_conn.query("""
            MATCH (j:Job {url: $url})
            DETACH DELETE j
        """, {"url": job_id})
        
        return {"code": 200, "message": "职位删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除职位失败: {str(e)}")

# 健康检查
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "enterprise", "port": 8002}

# 关闭事件
@app.on_event("shutdown")
def shutdown_event():
    neo4j_conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
