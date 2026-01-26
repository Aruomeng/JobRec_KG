"""
高校端后端服务
端口: 8003
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
import sys

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
        env_file = "../.env"

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

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# 请求模型
class LoginRequest(BaseModel):
    username: str
    password: str

# 创建FastAPI应用
app = FastAPI(title="高校端API", version="2.0.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 高校端API ====================

@app.get("/api/")
def read_root():
    return {"message": "高校端API"}

# 高校端登录API
@app.post("/api/university/login")
def university_login(request: LoginRequest):
    """高校端登录（使用Neon数据库）"""
    try:
        conn = get_neon_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, username, password_hash, display_name, role 
            FROM users 
            WHERE username = %s AND role = 'university'
        """, (request.username,))
        
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if not user:
            raise HTTPException(status_code=401, detail="用户不存在或非高校账号")
        
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

@app.get("/api/university/skill-gap")
def analyze_skill_gap(top_k: int = 20):
    """
    技能缺口分析：
    - 市场需求 = 职位对该技能的需求数
    - 课程供给 = 开设该技能相关课程的数量
    - 缺口分数 = 需求 / 供给（供给越少缺口越大）
    """
    query = """
    // 获取市场技能需求（职位数量）
    MATCH (j:Job)-[:REQUIRES_SKILL]->(sk:Skill)
    WITH sk.name AS skill, COUNT(DISTINCT j) AS market_demand
    WHERE market_demand >= 50  // 只看有一定需求量的技能
    
    // 获取课程供给（有多少门课程教这个技能）
    OPTIONAL MATCH (c:Course)-[:TEACHES_SKILL]->(sk2:Skill {name: skill})
    WITH skill, market_demand, COUNT(DISTINCT c) AS supply_count
    
    // 计算缺口分数（需求高但供给低的缺口大）
    WITH skill, market_demand, supply_count,
         CASE WHEN supply_count = 0 THEN market_demand 
              ELSE toFloat(market_demand) / supply_count 
         END AS gap_score
    ORDER BY gap_score DESC
    LIMIT $top_k
    
    // 获取相关课程名称
    OPTIONAL MATCH (c:Course)-[:TEACHES_SKILL]->(sk:Skill {name: skill})
    RETURN skill, market_demand, supply_count, gap_score, 
           COLLECT(DISTINCT c.name)[0..3] AS supply_courses
    """
    
    results = neo4j_conn.query(query, parameters={"top_k": top_k})
    
    # 格式化返回数据
    gaps = []
    max_gap = max([r["gap_score"] for r in results], default=1) if results else 1
    
    for r in results:
        supply_count = r["supply_count"] or 0
        supply_courses = r["supply_courses"] or []
        
        # 生成行动建议
        if supply_count == 0:
            action = "🔴 急需开设相关课程"
        elif supply_count <= 2:
            action = "🟠 建议增开更多课程"
        else:
            action = "🟢 加强现有课程深度"
        
        gap_item = {
            "skill": r["skill"],
            "market_demand": r["market_demand"],
            "supply_courses": supply_count,
            "gap_score": round(r["gap_score"] / max_gap * 100, 1),
            "teaching_courses": supply_courses,
            "action": action
        }
        gaps.append(gap_item)
    
    return {"gaps": gaps}

@app.get("/api/university/course-health")
def evaluate_courses(limit: int = 30):
    """
    课程健康度评估：
    - 选课人数 = TAKES关系数量
    - 教授技能数 = TEACHES_SKILL关系数量
    - 就业关联度 = 课程技能与热门职位需求的匹配度
    """
    query = """
    MATCH (c:Course)
    
    // 选课人数
    OPTIONAL MATCH (s:Student)-[:TAKES|ENROLLED_IN]->(c)
    WITH c, COUNT(DISTINCT s) AS enrollment
    
    // 教授技能
    OPTIONAL MATCH (c)-[:TEACHES_SKILL]->(sk:Skill)
    WITH c, enrollment, COLLECT(DISTINCT sk.name) AS skills, COUNT(DISTINCT sk) AS skill_count
    
    // 计算就业关联度（技能被职位需求的程度）
    UNWIND CASE WHEN SIZE(skills) > 0 THEN skills ELSE [null] END AS skill_name
    OPTIONAL MATCH (j:Job)-[:REQUIRES_SKILL]->(sk2:Skill {name: skill_name})
    WITH c, enrollment, skill_count, skills,
         SUM(CASE WHEN j IS NOT NULL THEN 1 ELSE 0 END) AS total_job_matches
    
    // 关联度 = 职位匹配总数 / 技能数（归一化）
    WITH c, enrollment, skill_count, skills, total_job_matches,
         CASE WHEN skill_count > 0 
              THEN toFloat(total_job_matches) / (skill_count * 100)
              ELSE 0 
         END AS relevance_raw
    
    RETURN c.name AS name, 
           enrollment, 
           skill_count, 
           skills[0..5] AS top_skills,
           total_job_matches,
           relevance_raw
    ORDER BY enrollment DESC, total_job_matches DESC
    LIMIT $limit
    """
    
    results = neo4j_conn.query(query, parameters={"limit": limit})
    
    # 格式化返回数据
    courses = []
    max_relevance = max([r["relevance_raw"] for r in results], default=1) if results else 1
    if max_relevance == 0:
        max_relevance = 1
    
    for i, r in enumerate(results):
        enrollment = r["enrollment"] or 0
        skill_count = r["skill_count"] or 0
        job_matches = r["total_job_matches"] or 0
        
        # 就业关联度归一化到0-1
        job_relevance = min(1.0, r["relevance_raw"] / max_relevance) if max_relevance > 0 else 0.3
        
        # 薪资贡献估算
        if job_matches > 500:
            salary_impact = round(0.1 + (job_matches / 10000), 2)
        elif job_matches > 100:
            salary_impact = round(0.05 + (job_matches / 20000), 2)
        elif job_matches > 0:
            salary_impact = round(job_matches / 50000, 2)
        else:
            salary_impact = -0.05
        
        # 趋势判断
        if enrollment >= 35 and job_relevance >= 0.5:
            trend = "📈 上升"
        elif enrollment >= 20 or job_relevance >= 0.3:
            trend = "➡️ 稳定"
        else:
            trend = "📉 下降"
        
        course_item = {
            "name": r["name"],
            "enrollment": enrollment,
            "skill_count": skill_count,
            "top_skills": r["top_skills"] or [],
            "job_relevance": round(job_relevance, 2),
            "salary_impact": salary_impact,
            "trend": trend
        }
        courses.append(course_item)
    
    return {"courses": courses}

@app.get("/api/university/reform-suggestions")
def get_reform_suggestions():
    """
    改革建议：基于技能缺口分析生成
    """
    try:
        # 1. 获取急需技能
        urgent_query = """
        MATCH (j:Job)-[:REQUIRES_SKILL]->(sk:Skill)
        WITH sk.name AS skill, COUNT(DISTINCT j) AS demand
        WHERE demand >= 100
        
        OPTIONAL MATCH (c:Course)-[:TEACHES_SKILL]->(sk2:Skill {name: skill})
        WITH skill, demand, COUNT(DISTINCT c) AS course_count
        WHERE course_count <= 1
        
        RETURN skill, demand, course_count
        ORDER BY demand DESC
        LIMIT 10
        """
        urgent_skills = neo4j_conn.query(urgent_query)
        
        # 2. 获取低效课程
        low_eff_query = """
        MATCH (c:Course)
        OPTIONAL MATCH (s:Student)-[:TAKES|ENROLLED_IN]->(c)
        WITH c, COUNT(DISTINCT s) AS enrollment
        WHERE enrollment < 20
        
        OPTIONAL MATCH (c)-[:TEACHES_SKILL]->(sk:Skill)<-[:REQUIRES_SKILL]-(j:Job)
        WITH c.name AS course, enrollment, COUNT(DISTINCT j) AS job_demand
        
        RETURN course, enrollment, 
               CASE WHEN job_demand > 0 THEN toFloat(enrollment) / (job_demand / 100.0) ELSE 0 END AS relevance
        ORDER BY relevance ASC
        LIMIT 10
        """
        low_eff_courses = neo4j_conn.query(low_eff_query)
        
        # 格式化急需技能
        urgent_list = []
        for u in urgent_skills:
            urgent_list.append({
                "skill": u["skill"],
                "demand": u["demand"],
                "course_count": u["course_count"]
            })
        
        # 格式化低效课程
        low_relevance_list = []
        for l in low_eff_courses:
            low_relevance_list.append({
                "course": l["course"],
                "relevance": round(l["relevance"] if l["relevance"] else 0, 2)
            })
        
        # 生成总结
        if urgent_list or low_relevance_list:
            summary = f"分析发现 {len(urgent_list)} 个急需开设课程的技能，{len(low_relevance_list)} 门需要评估的低效课程。建议重点关注 Python、Java、AI 等热门技术领域的课程建设。"
        else:
            summary = "当前课程体系较为健康，建议持续关注市场需求变化。"
        
        return {
            "summary": summary,
            "urgent_skills": urgent_list,
            "low_relevance_courses": low_relevance_list
        }
    except Exception as e:
        print(f"reform-suggestions error: {e}")
        return {
            "summary": "数据分析中，请稍后再试",
            "urgent_skills": [],
            "low_relevance_courses": []
        }

# 健康检查
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "university", "port": 8003}

# 关闭事件
@app.on_event("shutdown")
def shutdown_event():
    neo4j_conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True)
