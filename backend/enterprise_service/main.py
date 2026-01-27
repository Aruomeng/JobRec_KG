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

# 添加GraphSAGE推荐系统的路径
sys.path.append('/Users/tianyuhang/代码/jobrec/模块_推荐系统/深度学习GraphSAGE/源代码/核心模块')

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
        env_file = "/Users/tianyuhang/代码/jobrec/backend/.env"

# 初始化配置
settings = Settings()

# 密码上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Neo4j连接
class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def query(self, query, parameters=None):
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [record.data() for record in result]

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
