from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic_settings import BaseSettings
from pydantic import BaseModel, Field
from neo4j import GraphDatabase
from typing import List, Optional, Dict, Any
import math
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
import os
import sys

# 导入统一配置
from common import config

# 添加GraphSAGE推荐系统的路径 (使用配置)
sys.path.insert(0, str(config.GRAPHSAGE_MODULE_PATH))
from hybrid_recommender import create_recommender_from_trained_model

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
        env_file = ".env"
        extra = "ignore"

# 初始化配置
settings = Settings()

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
print(f"DEBUG: Connecting to Neo4j at {settings.neo4j_uri} with user {settings.neo4j_user}")
neo4j_conn = Neo4jConnection(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)

# 密码上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 初始化GraphSAGE推荐器
try:
    print("🔄 正在初始化GraphSAGE推荐器...")
    # 使用配置的模型路径和数据路径
    model_path = str(config.GRAPHSAGE_MODEL_PATH)
    data_path = str(config.GRAPHSAGE_DATA_PATH)
    
    # 创建推荐器实例
    graphsage_recommender = create_recommender_from_trained_model(
        model_path=model_path,
        data_path=data_path,
        neo4j_uri=settings.neo4j_uri,
        neo4j_user=settings.neo4j_user,
        neo4j_password=settings.neo4j_password
    )
    print("✅ GraphSAGE推荐器初始化成功!")
except Exception as e:
    print(f"❌ GraphSAGE推荐器初始化失败: {e}")
    graphsage_recommender = None

# 创建FastAPI应用
app = FastAPI(title="高校就业推荐系统API", version="1.0.0")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的前端地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 启动时创建 Neo4j 索引 (提升查询性能)
@app.on_event("startup")
async def create_neo4j_indexes():
    """创建关键字段索引以优化查询性能"""
    indexes = [
        "CREATE INDEX student_id_idx IF NOT EXISTS FOR (s:Student) ON (s.student_id)",
        "CREATE INDEX student_username_idx IF NOT EXISTS FOR (s:Student) ON (s.username)",
        "CREATE INDEX skill_name_idx IF NOT EXISTS FOR (sk:Skill) ON (sk.name)",
        "CREATE INDEX job_url_idx IF NOT EXISTS FOR (j:Job) ON (j.url)",
        "CREATE INDEX job_title_idx IF NOT EXISTS FOR (j:Job) ON (j.title)",
        "CREATE INDEX company_name_idx IF NOT EXISTS FOR (c:Company) ON (c.name)",
        "CREATE INDEX city_name_idx IF NOT EXISTS FOR (ct:City) ON (ct.name)",
        "CREATE INDEX course_name_idx IF NOT EXISTS FOR (c:Course) ON (c.name)",
    ]
    try:
        for idx_query in indexes:
            neo4j_conn.query(idx_query)
        print("✅ Neo4j 索引创建/验证完成")
    except Exception as e:
        print(f"⚠️ Neo4j 索引创建失败 (可能已存在): {e}")

# 模型类
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class Student(BaseModel):
    student_id: str
    name: str
    education: Optional[str] = None
    major: Optional[str] = None
    expected_position: Optional[str] = None
    skills: List[str] = Field(default_factory=list)

class StudentCreate(BaseModel):
    username: str
    password: str
    name: str
    education: Optional[str] = None
    major: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class JobRecommendationRequest(BaseModel):
    student_id: str
    top_k: int = 10
    city: Optional[str] = None

class SkillRecommendationRequest(BaseModel):
    skills: List[str]
    top_k: int = 20
    city: Optional[str] = None
    student_id: Optional[str] = None
    use_model: bool = False

class HybridRecommendationRequest(BaseModel):
    student_id: str
    recall_k: int = 500
    rank_k: int = 50
    final_k: int = 20
    weights: Optional[Dict[str, float]] = None
    city: Optional[str] = None
    salary: Optional[str] = None
    include_insight: bool = False

class CoursePathRequest(BaseModel):
    student_id: str
    target_job_id: str

class SkillDiagnosisRequest(BaseModel):
    student_id: str
    skills: List[str] = Field(default_factory=list)

class UpdateProfileRequest(BaseModel):
    student_id: str
    name: Optional[str] = None
    education: Optional[str] = None
    major: Optional[str] = None
    expected_position: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    courses: List[str] = Field(default_factory=list)

class SaveCoursesRequest(BaseModel):
    student_id: str
    courses: List[str]

class ScoutTalentsRequest(BaseModel):
    job_id: str
    top_k: int = 20
    education_filter: Optional[str] = None

class ResumeXRayRequest(BaseModel):
    student_id: str
    job_id: str

# 工具函数
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret_key, algorithm=settings.algorithm)
    return encoded_jwt

def sanitize_data(data):
    """
    递归处理数据中的 NaN 值，将其转换为 None，以便 JSON 序列化。
    """
    if isinstance(data, dict):
        return {k: sanitize_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_data(v) for v in data]
    elif isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None
        return data
    else:
        return data

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.PyJWTError:
        raise credentials_exception
    # 这里应该从数据库获取用户信息
    user = {"username": token_data.username}
    if user is None:
        raise credentials_exception
    return user

# 路由
@app.get("/api/")
def read_root():
    return {"message": "高校就业推荐系统API"}

# 学生端API
@app.get("/api/student/hot-jobs")
def get_hot_jobs(limit: int = 20):
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

@app.post("/api/student/recommend-jobs")
def recommend_jobs(request: JobRecommendationRequest):
    # 实现职位推荐逻辑
    query = """
    MATCH (s:Student {student_id: $student_id})-[:HAS_SKILL]->(sk:Skill)<-[:REQUIRES_SKILL]-(j:Job)
    """

    parameters = {
        "student_id": request.student_id,
        "top_k": 200  # 增加初始召回数量
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
    
    # 计算匹配率
    for result in results:
        match_count = result.pop("match_count")
        required_skills = result.get("required_skills") or []
        total_skills = len(required_skills)
        result["match_rate"] = match_count / total_skills if total_skills > 0 else 0
        result["match_score"] = result["match_rate"]
    
    # 过滤匹配度 >= 30% 的结果
    results = [r for r in results if r.get("match_rate", 0) >= 0.3]
    
    # 按匹配度从高到低排序
    results.sort(key=lambda x: x.get("match_rate", 0), reverse=True)
    
    return sanitize_data({"recommendations": results})

@app.post("/api/student/recommend-by-skills")
def recommend_by_skills(request: SkillRecommendationRequest):
    """基于技能推荐逻辑，支持 KG 和 AI 两种模式"""
    if not request.skills:
        return {"recommendations": []}
    
    print(f"DEBUG recommend_by_skills: city={request.city}, skills={request.skills}, use_model={request.use_model}")
    
    # AI 模式：使用 GraphSAGE 深度学习模型
    if request.use_model and graphsage_recommender:
        try:
            # 如果有学生 ID，使用混合推荐
            student_id = request.student_id or "anonymous"
            
            # 查询用户完整信息（期望职业、学历、课程）
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
            
            print(f"DEBUG AI推荐: expected_position={expected_position}, education={education}, courses_count={len(courses)}")
            
            # AI 推荐模式：使用纯深度学习推荐 + 规则加权
            recommendations = graphsage_recommender.recommend_pure_dl(
                student_id=student_id,
                top_k=request.top_k,
                city=request.city,
                skills=request.skills,
                expected_position=expected_position,
                education=education,
                courses=courses
            )
            
            # 格式化返回结果
            formatted_results = []
            for rec in recommendations:
                job_id = rec.job_id
                if '/' in job_id:
                    job_id = job_id.split('/')[-1]
                
                # 获取职位详情
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
                    # 处理城市：使用职位的实际城市（城市过滤后应该匹配）
                    cities = [c for c in (job_info.get("cities") or []) if c]
                    if cities:
                        # 如果用户选择了城市，优先显示匹配的城市
                        if request.city and request.city in cities:
                            display_city = request.city
                        else:
                            display_city = cities[0]  # 使用实际城市
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
            
            # AI 模式分数体系不同，不需要 0.3 阈值过滤
            # 按匹配度从高到低排序
            formatted_results.sort(key=lambda x: x.get("match_rate", 0), reverse=True)
            
            return sanitize_data({"recommendations": formatted_results, "algorithm": "Deep Learning (GraphSAGE)"})
        except Exception as e:
            print(f"GraphSAGE 推荐失败, 回退到 KG 模式: {e}")
            # 回退到 KG 模式
    
    # KG 模式：使用知识图谱技能匹配
    if request.city:
        print(f"DEBUG KG城市过滤: 用户选择城市={request.city}")
        # 直接在路径中匹配城市
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
        parameters = {
            "skills": request.skills,
            "top_k": request.top_k,
            "city": request.city
        }
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
        parameters = {
            "skills": request.skills,
            "top_k": request.top_k
        }
    
    results = neo4j_conn.query(query, parameters=parameters)
    
    print(f"DEBUG KG模式: city={request.city}, 查询结果数={len(results)}")
    
    # 查询用户期望职业（用于加权）
    expected_position = None
    if request.student_id:
        user_query = "MATCH (s:Student {student_id: $sid}) RETURN s.expected_position as pos"
        user_result = neo4j_conn.query(user_query, parameters={"sid": request.student_id})
        if user_result and user_result[0]:
            expected_position = user_result[0].get("pos")
    
    # 计算匹配率和期望职业加权
    for result in results:
        matched_skills = result.get("matched_skills", [])
        required_skills = result.get("required_skills") or []
        total_skills = len(required_skills)
        skill_match_rate = len(matched_skills) / total_skills if total_skills > 0 else 0
        
        # 期望职业加权（KG模式：温和加权，让技能匹配主导）
        position_boost = 1.0
        job_title = result.get("title", "").lower() if result.get("title") else ""
        if expected_position and job_title:
            expected_lower = expected_position.lower()
            if expected_lower in job_title or job_title in expected_lower:
                position_boost = 1.15  # 温和完全匹配（原1.5）
            else:
                # 关键词匹配
                keywords = expected_lower.split()
                match_count = sum(1 for kw in keywords if kw in job_title)
                if match_count > 0:
                    position_boost = 1.0 + 0.05 * (match_count / len(keywords))  # 温和（原0.3）
        
        result["match_rate"] = skill_match_rate * position_boost
        result["match_score"] = result["match_rate"]
        result["position_match"] = position_boost > 1.0
        result["skill_coverage"] = f"{len(matched_skills)}/{total_skills}"  # 新增：技能覆盖率
    
    # 过滤匹配度 >= 30% 的结果
    results = [r for r in results if r.get("match_rate", 0) >= 0.3]
    
    # 按匹配度从高到低排序（带期望职业加权）
    results.sort(key=lambda x: x.get("match_rate", 0), reverse=True)
    
    return sanitize_data({"recommendations": results, "algorithm": "Knowledge Graph Based"})

@app.post("/api/student/login")
def student_login(request: LoginRequest):
    # 实现学生登录逻辑
    query = """
    MATCH (s:Student {username: $username})
    OPTIONAL MATCH (s)-[:HAS_SKILL]->(sk:Skill)
    OPTIONAL MATCH (s)-[:ENROLLED_IN]->(c:Course)
    RETURN s.student_id AS student_id, s.name AS name, s.password AS password, 
           s.education AS education, s.major AS major, s.expected_position AS expected_position,
           COLLECT(DISTINCT sk.name) AS skills, COLLECT(DISTINCT c.name) AS courses
    """
    
    results = neo4j_conn.query(query, parameters={"username": request.username})
    
    # 检查是否有结果且student_id不为空（表示用户存在）
    if not results or results[0].get("student_id") is None:
        # 如果用户不存在，创建新用户
        count_result = neo4j_conn.query('MATCH (s:Student) RETURN COUNT(s) AS count')
        new_student_id = f"STU{count_result[0]['count'] + 1:04d}"
        hashed_password = get_password_hash(request.password)
        
        create_query = """
        CREATE (s:Student {student_id: $student_id, username: $username, password: $password, 
                         name: $username, joined_at: datetime()})
        RETURN s.student_id AS student_id, s.name AS name, s.education AS education, 
               s.major AS major, s.expected_position AS expected_position
        """
        
        create_result = neo4j_conn.query(create_query, parameters={
            "student_id": new_student_id,
            "username": request.username,
            "password": hashed_password
        })
        
        return {
            "code": 200,
            "data": {
                **create_result[0],
                "skills": [],
                "courses": []
            }
        }
    
    student = results[0]
    stored_password = student.pop("password", None)
    
    # 如果用户有密码，验证密码
    if stored_password:
        if not verify_password(request.password, stored_password):
            raise HTTPException(status_code=401, detail="Incorrect password")
    # 如果用户没有密码（旧数据），设置密码
    else:
        hashed_password = get_password_hash(request.password)
        neo4j_conn.query(
            "MATCH (s:Student {student_id: $student_id}) SET s.password = $password",
            parameters={"student_id": student["student_id"], "password": hashed_password}
        )
    
    return {
        "code": 200,
        "data": student
    }

@app.post("/api/student/parse-resume")
def upload_resume(file: UploadFile = File(...)):
    # 实现简历解析逻辑
    # 这里只是模拟实现，实际需要使用PDF/Word解析库
    skills = ["Python", "Java", "SQL", "数据分析"]
    return {"skills": skills, "message": "Resume parsed successfully"}

@app.post("/api/student/course-path")
def plan_course_path(request: CoursePathRequest):
    # 实现课程规划逻辑
    query = """
    MATCH (j:Job {job_id: $target_job_id})-[:REQUIRES_SKILL]->(sk:Skill)<-[:TEACHES]-(c:Course)
    RETURN c.name AS name, c.course_id AS course_id, COLLECT(sk.name) AS covers
    ORDER BY SIZE(covers) DESC
    """
    
    results = neo4j_conn.query(query, parameters={"target_job_id": request.target_job_id})
    return {"course_path": results}

@app.post("/api/student/skill-diagnosis")
def diagnose_skills(request: SkillDiagnosisRequest):
    """
    技能诊断：个性化职业导向的技能分析
    - 合并直接技能 + 课程关联技能
    - 根据期望职业分析技能匹配和缺口
    - 比较同期望职业的其他学生
    """
    student_id = request.student_id
    
    # 1. 获取用户基本信息和期望职业
    profile_query = """
    MATCH (s:Student {student_id: $student_id})
    RETURN s.expected_position AS expected_position, s.education AS education, s.major AS major
    """
    profile_result = neo4j_conn.query(profile_query, parameters={"student_id": student_id})
    expected_position = profile_result[0]["expected_position"] if profile_result else None
    education = profile_result[0]["education"] if profile_result else None
    major = profile_result[0]["major"] if profile_result else None
    
    # 2. 获取直接技能 + 课程关联技能
    skills_query = """
    // 直接技能
    OPTIONAL MATCH (s:Student {student_id: $student_id})-[:HAS_SKILL]->(sk1:Skill)
    WITH COLLECT(DISTINCT sk1.name) AS direct_skills
    
    // 课程关联技能
    OPTIONAL MATCH (s2:Student {student_id: $student_id})-[:TAKES]->(c:Course)-[:TEACHES_SKILL]->(sk2:Skill)
    WITH direct_skills, COLLECT(DISTINCT sk2.name) AS course_skills
    
    // 合并去重
    WITH direct_skills, course_skills, 
         [x IN direct_skills + course_skills WHERE x IS NOT NULL | x] AS all_raw
    UNWIND all_raw AS skill
    WITH direct_skills, course_skills, COLLECT(DISTINCT skill) AS all_skills
    
    RETURN direct_skills, course_skills, all_skills
    """
    skills_result = neo4j_conn.query(skills_query, parameters={"student_id": student_id})
    
    if skills_result:
        direct_skills = [s for s in skills_result[0]["direct_skills"] if s]
        course_skills = [s for s in skills_result[0]["course_skills"] if s]
        all_skills = [s for s in skills_result[0]["all_skills"] if s]
    else:
        direct_skills, course_skills, all_skills = [], [], []
    
    if not all_skills:
        return {
            "expected_position": expected_position,
            "skills_analysis": {"direct_skills": [], "course_skills": [], "all_skills": []},
            "position_analysis": {"required_skills": [], "matched_skills": [], "missing_skills": [], "match_rate": 0},
            "market_analysis": {"hot_skills": [], "matched_hot_skills": [], "market_match_rate": 0},
            "recommended_courses": [],
            "peer_comparison": {"avg_skills_count": 0, "your_rank_percentile": 0, "top_skills_in_peers": []},
            "diagnosis": {"overall": "请完善您的技能信息或选择课程以获得更准确的诊断结果。", "strengths": [], "suggestions": ["添加技能", "选择课程"]}
        }
    
    # 3. 期望职业技能分析
    position_skills = []
    if expected_position:
        # 查询期望职业相关职位的技能需求
        position_query = """
        MATCH (j:Job)-[:REQUIRES_SKILL]->(sk:Skill)
        WHERE j.title CONTAINS $position
        WITH sk.name AS skill, COUNT(j) AS demand
        ORDER BY demand DESC
        LIMIT 15
        RETURN skill, demand
        """
        position_results = neo4j_conn.query(position_query, parameters={"position": expected_position})
        position_skills = [{"name": r["skill"], "demand": r["demand"], "mastered": r["skill"] in all_skills} 
                          for r in position_results]
    
    matched_position_skills = [s["name"] for s in position_skills if s["mastered"]]
    missing_position_skills = [s["name"] for s in position_skills if not s["mastered"]]
    position_match_rate = round(len(matched_position_skills) / len(position_skills) * 100, 2) if position_skills else 0
    
    # 4. 市场热门技能分析（保留原有功能）
    hot_query = """
    MATCH (j:Job)-[:REQUIRES_SKILL]->(sk:Skill)
    WITH sk.name AS skill, COUNT(j) AS demand
    ORDER BY demand DESC
    LIMIT 20
    RETURN skill, demand
    """
    hot_results = neo4j_conn.query(hot_query)
    hot_skills = [{"name": r["skill"], "demand": r["demand"]} for r in hot_results]
    matched_hot_skills = [s["name"] for s in hot_skills if s["name"] in all_skills]
    market_match_rate = round(len(matched_hot_skills) / len(hot_skills) * 100, 2) if hot_skills else 0
    
    # 5. 同行对比（包含直接技能 + 课程技能）- 多级回退匹配
    # 通用同行查询模板
    def build_peer_query(where_clause):
        return f"""
        MATCH (s:Student)
        WHERE {where_clause} AND s.student_id <> $student_id
        
        // 获取每个学生的所有技能（直接 + 课程）
        OPTIONAL MATCH (s)-[:HAS_SKILL]->(sk1:Skill)
        OPTIONAL MATCH (s)-[:TAKES]->(:Course)-[:TEACHES_SKILL]->(sk2:Skill)
        WITH s, COLLECT(DISTINCT sk1.name) + COLLECT(DISTINCT sk2.name) AS all_skill_names
        WITH s, [x IN all_skill_names WHERE x IS NOT NULL | x] AS skills
        WITH s, SIZE(skills) AS skill_count, skills
        
        // 统计平均技能数和热门技能
        WITH COLLECT(skill_count) AS all_counts, COLLECT(skills) AS all_skills_lists
        UNWIND all_skills_lists AS skill_list
        UNWIND skill_list AS skill
        WITH all_counts, skill, COUNT(*) AS freq
        ORDER BY freq DESC
        WITH all_counts, COLLECT(skill)[0..5] AS top_skills
        
        // 计算平均值
        WITH top_skills, 
             CASE WHEN SIZE(all_counts) > 0 THEN REDUCE(sum=0.0, x IN all_counts | sum + x) / SIZE(all_counts) ELSE 0 END AS avg_count,
             SIZE(all_counts) AS peer_count
        
        RETURN avg_count, peer_count, top_skills
        """
    
    peer_data = None
    peer_match_type = None  # 用于记录匹配类型
    
    # 优先级1: 按期望职业匹配
    if expected_position:
        peer_query = build_peer_query("s.expected_position = $position")
        peer_result = neo4j_conn.query(peer_query, parameters={"position": expected_position, "student_id": student_id})
        if peer_result and peer_result[0]["peer_count"] > 0:
            peer_data = peer_result[0]
            peer_match_type = "expected_position"
    
    # 优先级2: 按专业匹配
    if not peer_data and major:
        peer_query = build_peer_query("s.major = $major")
        peer_result = neo4j_conn.query(peer_query, parameters={"major": major, "student_id": student_id})
        if peer_result and peer_result[0]["peer_count"] > 0:
            peer_data = peer_result[0]
            peer_match_type = "major"
    
    # 优先级3: 按学历匹配
    if not peer_data and education:
        peer_query = build_peer_query("s.education = $education")
        peer_result = neo4j_conn.query(peer_query, parameters={"education": education, "student_id": student_id})
        if peer_result and peer_result[0]["peer_count"] > 0:
            peer_data = peer_result[0]
            peer_match_type = "education"
    
    # 优先级4: 全局平均（兜底）
    if not peer_data:
        peer_query = build_peer_query("s.student_id IS NOT NULL")
        peer_result = neo4j_conn.query(peer_query, parameters={"student_id": student_id})
        if peer_result and peer_result[0]["peer_count"] > 0:
            peer_data = peer_result[0]
            peer_match_type = "global"
    
    # 解析同行数据
    if peer_data:
        avg_skills_count = round(peer_data["avg_count"], 1)
        top_skills_in_peers = [s for s in peer_data["top_skills"] if s][:5]
        # 计算百分位排名
        your_count = len(all_skills)
        rank_percentile = min(100, round(your_count / max(avg_skills_count, 1) * 50, 0))
    else:
        # 无同行数据时（理论上不会发生，除非数据库为空）
        avg_skills_count = 0
        top_skills_in_peers = []
        rank_percentile = 50
        peer_match_type = None
    
    # 6. 推荐课程（根据期望职业缺失技能）
    gap_skills = missing_position_skills[:5] if missing_position_skills else [s["name"] for s in hot_skills if s["name"] not in all_skills][:5]
    
    if gap_skills:
        course_query = """
        UNWIND $skills AS skill_name
        MATCH (c:Course)-[:TEACHES_SKILL]->(sk:Skill {name: skill_name})
        WITH c, COLLECT(DISTINCT sk.name) AS covers
        RETURN c.name AS name, covers, SIZE(covers) AS priority
        ORDER BY priority DESC
        LIMIT 4
        """
        course_results = neo4j_conn.query(course_query, parameters={"skills": gap_skills})
        recommended_courses = [{"name": r["name"], "covers": r["covers"], "priority": r["priority"]} for r in course_results]
    else:
        recommended_courses = []
    
    # 7. 生成诊断结论
    strengths = []
    suggestions = []
    
    if len(direct_skills) >= 5:
        strengths.append(f"已掌握 {len(direct_skills)} 项核心技能")
    if len(course_skills) >= 3:
        strengths.append(f"通过 {len(set(course_skills))} 门课程拓展了技能")
    if position_match_rate >= 50:
        strengths.append(f"与期望职业『{expected_position}』匹配度较高")
    if matched_hot_skills:
        strengths.append(f"掌握 {len(matched_hot_skills)} 项热门技能")
    
    if missing_position_skills:
        suggestions.append(f"建议学习 {missing_position_skills[0]} 提升竞争力")
    if position_match_rate < 50 and expected_position:
        suggestions.append(f"增加『{expected_position}』领域技能学习")
    if len(all_skills) < avg_skills_count:
        suggestions.append("技能数量低于同行平均，建议拓展技能面")
    if recommended_courses:
        suggestions.append(f"推荐学习《{recommended_courses[0]['name']}》课程")
    
    if position_match_rate >= 70:
        overall = f"恭喜！您在『{expected_position}』领域的技能非常出色（匹配度 {position_match_rate}%），继续保持！"
    elif position_match_rate >= 50:
        overall = f"您在『{expected_position}』领域有良好基础（匹配度 {position_match_rate}%），补充核心技能后将更具竞争力。"
    elif position_match_rate >= 30:
        overall = f"您在『{expected_position}』领域还需提升（匹配度 {position_match_rate}%），建议重点学习该领域核心技能。"
    elif expected_position:
        overall = f"您与『{expected_position}』领域有一定差距（匹配度 {position_match_rate}%），建议系统学习相关课程。"
    else:
        overall = "请设置期望职业以获得更精准的技能诊断。"
    
    return {
        "expected_position": expected_position,
        "education": education,
        "major": major,
        "skills_analysis": {
            "direct_skills": direct_skills,
            "course_skills": course_skills,
            "all_skills": all_skills
        },
        "position_analysis": {
            "required_skills": position_skills,
            "matched_skills": matched_position_skills,
            "missing_skills": missing_position_skills,
            "match_rate": position_match_rate
        },
        "market_analysis": {
            "hot_skills": [s["name"] for s in hot_skills],
            "matched_hot_skills": matched_hot_skills,
            "market_match_rate": market_match_rate
        },
        "recommended_courses": recommended_courses,
        "peer_comparison": {
            "avg_skills_count": avg_skills_count,
            "your_rank_percentile": rank_percentile,
            "top_skills_in_peers": top_skills_in_peers
        },
        "diagnosis": {
            "overall": overall,
            "strengths": strengths if strengths else ["努力学习中"],
            "suggestions": suggestions if suggestions else ["保持当前状态"]
        }
    }

@app.get("/api/student/get-courses")
def get_courses(major: Optional[str] = None):
    """
    获取可选课程列表
    - 如果提供专业参数，优先返回该专业相关的课程
    - 如果没有专业或专业无课程，返回热门课程（按选课人数排序）
    """
    courses = []
    
    # 如果有专业，尝试获取专业相关课程
    if major:
        major_query = """
        MATCH (m:Major)-[:HAS_COURSE]->(c:Course)
        WHERE m.name CONTAINS $major OR $major CONTAINS m.name
        OPTIONAL MATCH (c)-[:TEACHES_SKILL]->(sk:Skill)
        WITH c, COLLECT(DISTINCT sk.name) AS skills
        RETURN c.name AS name, skills
        ORDER BY c.name
        LIMIT 50
        """
        results = neo4j_conn.query(major_query, parameters={"major": major})
        if results:
            courses = results
    
    # 如果没有专业课程，返回热门课程（按选课人数排序）
    if not courses:
        popular_query = """
        MATCH (c:Course)
        OPTIONAL MATCH (s:Student)-[:TAKES]->(c)
        OPTIONAL MATCH (c)-[:TEACHES_SKILL]->(sk:Skill)
        WITH c, COUNT(DISTINCT s) AS popularity, COLLECT(DISTINCT sk.name) AS skills
        RETURN c.name AS name, skills, popularity
        ORDER BY popularity DESC
        LIMIT 50
        """
        courses = neo4j_conn.query(popular_query)
    
    return {"courses": courses}

@app.post("/api/student/save-courses")
def save_courses(request: SaveCoursesRequest):
    """
    保存学生课程选择逻辑
    注意：不再自动将课程技能添加到 HAS_SKILL
    课程技能通过 TAKES->Course->TEACHES_SKILL 路径在推荐时推理
    """
    # 首先删除旧的课程关系
    delete_query = """
    MATCH (s:Student {student_id: $student_id})-[r:TAKES]->(:Course)
    DELETE r
    """
    neo4j_conn.query(delete_query, parameters={"student_id": request.student_id})
    
    # 添加新的课程关系
    if not request.courses:
        return {"courses_saved": 0, "acquired_skills": []}
    
    query = """
    MATCH (s:Student {student_id: $student_id})
    UNWIND $courses AS course_name
    MATCH (c:Course {name: course_name})
    MERGE (s)-[:TAKES]->(c)
    
    // 查询课程教授的技能（仅用于返回，不创建 HAS_SKILL 关系）
    WITH s, c
    OPTIONAL MATCH (c)-[:TEACHES_SKILL]->(sk:Skill)
    
    RETURN COUNT(DISTINCT c) AS courses_saved,
           COLLECT(DISTINCT sk.name) AS acquired_skills
    """
    
    results = neo4j_conn.query(query, parameters={
        "student_id": request.student_id,
        "courses": request.courses
    })
    
    return results[0] if results else {"courses_saved": 0, "acquired_skills": []}

@app.get("/api/student/get-profile/{student_id}")
def get_profile(student_id: str):
    """获取用户完整信息（包括技能和课程）"""
    query = """
    MATCH (s:Student {student_id: $student_id})
    OPTIONAL MATCH (s)-[:HAS_SKILL]->(sk:Skill)
    OPTIONAL MATCH (s)-[:TAKES]->(c:Course)
    RETURN s.student_id AS student_id, s.name AS name, 
           s.education AS education, s.major AS major, 
           s.expected_position AS expected_position,
           COLLECT(DISTINCT sk.name) AS skills,
           COLLECT(DISTINCT c.name) AS courses
    """
    results = neo4j_conn.query(query, parameters={"student_id": student_id})
    if not results or not results[0].get("student_id"):
        raise HTTPException(status_code=404, detail="User not found")
    return {"code": 200, "data": results[0]}

@app.post("/api/student/update-profile")
def update_profile(request: UpdateProfileRequest):
    # 实现更新个人信息逻辑
    # 首先更新基本信息
    update_basic_query = """
    MERGE (s:Student {student_id: $student_id})
    SET s.name = COALESCE($name, s.name),
        s.education = COALESCE($education, s.education),
        s.major = COALESCE($major, s.major),
        s.expected_position = COALESCE($expected_position, s.expected_position)
    RETURN s.student_id AS student_id
    """
    
    neo4j_conn.query(update_basic_query, parameters={
        "student_id": request.student_id,
        "name": request.name,
        "education": request.education,
        "major": request.major,
        "expected_position": request.expected_position
    })
    
    # 删除现有的技能关系
    delete_skills_query = """
    MATCH (s:Student {student_id: $student_id})-[r:HAS_SKILL]->()
    DELETE r
    """
    neo4j_conn.query(delete_skills_query, parameters={"student_id": request.student_id})
    
    # 添加新的技能关系（如果有技能）
    if request.skills:
        print(f"DEBUG update-profile: 添加 {len(request.skills)} 个技能")
        # 使用批量操作，只 MATCH 现有技能（不创建新技能）
        add_skills_query = """
        MATCH (s:Student {student_id: $student_id})
        UNWIND $skills AS skill_name
        MATCH (sk:Skill {name: skill_name})
        MERGE (s)-[:HAS_SKILL]->(sk)
        """
        neo4j_conn.query(add_skills_query, parameters={
            "student_id": request.student_id,
            "skills": request.skills
        })
        print(f"DEBUG update-profile: 技能添加完成")
    
    # 处理课程（如果有）
    if hasattr(request, 'courses') and request.courses:
        print(f"DEBUG update-profile: 添加 {len(request.courses)} 个课程")
        # 删除现有课程关系
        delete_courses_query = """
        MATCH (s:Student {student_id: $student_id})-[r:ENROLLED_IN]->()
        DELETE r
        """
        neo4j_conn.query(delete_courses_query, parameters={"student_id": request.student_id})
        
        # 添加新课程关系
        add_courses_query = """
        MATCH (s:Student {student_id: $student_id})
        UNWIND $courses AS course_name
        MATCH (c:Course {name: course_name})
        MERGE (s)-[:ENROLLED_IN]->(c)
        """
        neo4j_conn.query(add_courses_query, parameters={
            "student_id": request.student_id,
            "courses": request.courses
        })
        print(f"DEBUG update-profile: 课程添加完成")
    
    # 获取更新后的信息
    get_profile_query = """
    MATCH (s:Student {student_id: $student_id})
    OPTIONAL MATCH (s)-[:HAS_SKILL]->(sk:Skill)
    OPTIONAL MATCH (s)-[:ENROLLED_IN]->(c:Course)
    RETURN s.student_id AS student_id, s.name AS name, s.education AS education, 
           s.major AS major, s.expected_position AS expected_position,
           COLLECT(DISTINCT sk.name) AS skills, COLLECT(DISTINCT c.name) AS courses
    """
    result = neo4j_conn.query(get_profile_query, parameters={"student_id": request.student_id})
    
    return {"message": "Profile updated successfully", "data": result[0] if result else None}

@app.get("/api/job/detail/{job_id:path}")
def get_job_detail(job_id: str):
    # 实现获取职位详情逻辑
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
    # 处理城市：过滤None，取第一个有效城市
    cities = [c for c in (result.get("cities") or []) if c]
    result["city"] = cities[0] if cities else "不限"
    result["cities"] = cities
    
    return sanitize_data(result)

@app.post("/api/job/{job_id:path}/graph")
def get_job_graph(job_id: str, request_body: Optional[Dict] = Body(default=None)):
    # 从请求体中获取 user_skills
    user_skills = request_body.get("user_skills", []) if request_body else []
    
    # 实现获取职位知识图谱逻辑
    # 1. 核心技能与课程
    query = """
    MATCH (j:Job {url: $job_id})-[:REQUIRES_SKILL]->(sk:Skill)
    OPTIONAL MATCH (sk)<-[:TEACHES_SKILL]-(c:Course)
    RETURN sk.name AS skill, COLLECT(DISTINCT c.name) AS courses
    """
    
    results = neo4j_conn.query(query, parameters={"job_id": job_id})
    
    # 2. 城市与行业及标题
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
        # 优先使用前端传递的城市（推荐列表中显示的城市）
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
    
    # 添加城市和行业节点（可选，增强视觉）
    if job_info["city"]:
        nodes.append({"id": "city", "label": "City", "name": job_info["city"]})
        edges.append({"source": "job", "target": "city", "type": "LOCATED_IN"})
    
    if job_info["industry"]:
        nodes.append({"id": "industry", "label": "Industry", "name": job_info["industry"]})
        edges.append({"source": "job", "target": "industry", "type": "BELONGS_TO"})

    # 技能模糊匹配函数
    def skill_fuzzy_match(required_skill: str, user_skills: list) -> bool:
        """
        模糊匹配技能：
        - 精确匹配
        - 用户技能包含职位要求技能（如 "Java语言程序设计" 包含 "Java"）
        - 职位要求技能包含用户技能（如 "Python" 匹配 "Python开发"）
        """
        if not user_skills:
            return False
        
        required_lower = required_skill.lower()
        
        for user_skill in user_skills:
            user_lower = user_skill.lower()
            # 精确匹配
            if required_lower == user_lower:
                return True
            # 用户技能包含职位要求技能
            if required_lower in user_lower:
                return True
            # 职位要求技能包含用户技能
            if user_lower in required_lower:
                return True
        
        return False
    
    # 添加技能和课程
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

@app.post("/api/student/hybrid-recommend")
def hybrid_recommend(request: HybridRecommendationRequest):
    # 检查GraphSAGE推荐器是否可用
    if not graphsage_recommender:
        raise HTTPException(status_code=503, detail="GraphSAGE推荐器服务不可用")
    
    try:
        # 准备权重参数
        weights = request.weights
        if weights:
            # 确保权重格式正确
            weight_tuple = (weights.get('deep', 0.6), weights.get('skill', 0.3), weights.get('rule', 0.1))
        else:
            weight_tuple = (0.6, 0.3, 0.1)
        
        # 查询学生技能（用于冷启动用户的嵌入生成）
        skills_query = """
        MATCH (s:Student {student_id: $student_id})-[:HAS_SKILL]->(sk:Skill)
        RETURN collect(sk.name) as skills
        """
        skills_result = neo4j_conn.query(skills_query, parameters={"student_id": request.student_id})
        student_skills = skills_result[0]["skills"] if skills_result and skills_result[0]["skills"] else []
        
        # 使用GraphSAGE推荐器获取推荐结果
        recommendations = graphsage_recommender.recommend(
            student_id=request.student_id,
            recall_k=request.recall_k,
            rank_k=request.rank_k,
            final_k=request.final_k,
            weights=weight_tuple,
            city=request.city,
            skills=student_skills  # 传入学生技能用于冷启动嵌入生成
        )
        
        # 从Neo4j获取职位详细信息并格式化结果
        formatted_results = []
        for rec in recommendations:
            # 提取job_id（处理可能的URL格式）
            job_id = rec.job_id
            if '/' in job_id:
                job_id = job_id.split('/')[-1]
            
            # 查询职位详细信息
            # 查询职位详细信息
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
                
                # 查询课程->技能推理路径（如果开启洞察模式）
                insight = None
                if request.include_insight:
                    # 先查询直接技能
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
                    
                    # 再查询课程赋予的技能（排除直接技能）
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
                    
                    # 先添加直接技能
                    for skill in direct_skills:
                        skill_paths.append({
                            "skill": skill,
                            "sources": [],
                            "direct_match": True
                        })
                    
                    # 再添加课程赋予的技能（排除已有的直接技能）
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
                    # 如果用户选择了城市，使用用户选择的城市（因为推荐器已经过滤过了）
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
        
        # 过滤匹配度 >= 30% 的结果
        formatted_results = [r for r in formatted_results if r.get("match_rate", 0) >= 0.3]
        
        return sanitize_data({"recommendations": formatted_results})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"推荐失败: {str(e)}")

# 企业端API
@app.post("/api/enterprise/scout-talents")
def scout_talents(request: ScoutTalentsRequest):
    """人才召回：根据职位要求找到匹配的学生"""
    # 处理 job_id（可能是 URL 或后缀或技能关键词）
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
    
    print(f"DEBUG scout-talents: job_skills from job query = {job_skills}")
    
    # 如果没有通过职位找到技能，尝试将输入作为技能关键词直接搜索
    if not job_skills:
        # 检查输入是否匹配某个技能名称
        skill_check_query = """
        MATCH (sk:Skill)
        WHERE sk.name CONTAINS $keyword OR toLower(sk.name) CONTAINS toLower($keyword)
        RETURN COLLECT(sk.name) AS skills
        LIMIT 20
        """
        skill_result = neo4j_conn.query(skill_check_query, parameters={"keyword": job_id})
        job_skills = skill_result[0]["skills"] if skill_result and skill_result[0]["skills"] else []
        print(f"DEBUG scout-talents: job_skills from skill search = {job_skills}")
    
    if not job_skills:
        print(f"DEBUG scout-talents: No skills found for '{job_id}'")
        return {"candidates": []}
    
    # 查找匹配的学生（包含直接技能和通过课程获得的技能）
    query = """
    // 从所有学生开始
    MATCH (s:Student)
    
    // 直接拥有的技能
    OPTIONAL MATCH (s)-[:HAS_SKILL]->(sk1:Skill)
    WHERE sk1.name IN $job_skills
    WITH s, COLLECT(DISTINCT sk1.name) AS direct_skills
    
    // 通过课程获得的技能
    OPTIONAL MATCH (s)-[:TAKES|ENROLLED_IN]->(c:Course)-[:TEACHES_SKILL]->(sk2:Skill)
    WHERE sk2.name IN $job_skills
    WITH s, direct_skills, COLLECT(DISTINCT sk2.name) AS course_skills
    
    // 通过专业获得的技能
    OPTIONAL MATCH (s)-[:MAJORS_IN]->(m:Major)-[:HAS_COURSE]->(c2:Course)-[:TEACHES_SKILL]->(sk3:Skill)
    WHERE sk3.name IN $job_skills
    WITH s, direct_skills, course_skills, COLLECT(DISTINCT sk3.name) AS major_skills
    
    // 合并所有技能（去重）
    WITH s, apoc.coll.toSet(direct_skills + course_skills + major_skills) AS matched_skills
    WHERE SIZE(matched_skills) > 0
    
    RETURN s.student_id AS student_id, s.name AS name, s.education AS education, 
           s.major AS major, matched_skills, SIZE(matched_skills) AS match_count
    ORDER BY match_count DESC LIMIT $top_k
    """
    
    try:
        results = neo4j_conn.query(query, parameters={
            "job_skills": job_skills,
            "top_k": request.top_k
        })
    except Exception as e:
        # 如果 apoc 不可用，使用简化查询
        print(f"DEBUG scout-talents: APOC error, using simple query: {e}")
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
    
    print(f"DEBUG scout-talents: Found {len(results)} candidates, education_filter={request.education_filter}")
    
    # 格式化返回数据以匹配前端预期
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
    
    # 学历筛选：如果设置了 education_filter，过滤不匹配的候选人
    if request.education_filter:
        candidates = [c for c in candidates if c["education"] == request.education_filter]
        print(f"DEBUG scout-talents: After education filter '{request.education_filter}', {len(candidates)} candidates remain")
    
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

# 高校端API
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
    
    # 格式化返回数据以匹配前端预期
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
            "market_demand": r["market_demand"],  # 市场需求（职位数）
            "supply_courses": supply_count,  # 课程供给数
            "gap_score": round(r["gap_score"] / max_gap * 100, 1),  # 归一化到0-100
            "teaching_courses": supply_courses,  # 开设该技能的课程列表
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
    - 薪资贡献 = 基于技能需求量估算
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
        
        # 薪资贡献估算（基于技能需求量）
        if job_matches > 500:
            salary_impact = round(0.1 + (job_matches / 10000), 2)
        elif job_matches > 100:
            salary_impact = round(0.05 + (job_matches / 20000), 2)
        elif job_matches > 0:
            salary_impact = round(job_matches / 50000, 2)
        else:
            salary_impact = -0.05
        
        # 趋势判断（基于选课人数和就业关联度）
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
    - 急需技能：市场需求高但课程供给少
    - 低效课程：选课人少且就业关联度低
    """
    try:
        # 1. 获取急需技能（市场需求高但无课程供给的技能）
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
        
        # 2. 获取低效课程（选课少且技能需求量低）
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
        import traceback
        traceback.print_exc()
        return {
            "summary": "数据分析中，请稍后再试",
            "urgent_skills": [],
            "low_relevance_courses": []
        }

# 通用API
@app.get("/api/common/cities")
def get_cities():
    print("DEBUG: get_cities called")
    # 实现获取城市列表逻辑
    query = """
    MATCH (c:City)
    RETURN DISTINCT c.name AS city
    ORDER BY city
    """
    
    results = neo4j_conn.query(query)
    print(f"DEBUG: database results: {results}")
    return {"cities": [r["city"] for r in results if r["city"]]}

@app.get("/api/debug/data-stats")
def debug_data_stats():
    """调试：检查数据库中公司和城市分布"""
    # 公司分布
    company_query = """
    MATCH (j:Job)-[:OFFERED_BY]->(c:Company)
    RETURN c.name as company, count(j) as jobs
    ORDER BY jobs DESC LIMIT 20
    """
    companies = neo4j_conn.query(company_query)
    
    # 城市分布
    city_query = """
    MATCH (c:Company)-[:LOCATED_IN]->(ct:City)
    RETURN ct.name as city, count(c) as companies
    ORDER BY companies DESC
    """
    cities = neo4j_conn.query(city_query)
    
    # 检查外企德科在哪些城市
    waiqideke_query = """
    MATCH (c:Company)-[:LOCATED_IN]->(ct:City)
    WHERE c.name CONTAINS '外企德科'
    RETURN c.name as company, ct.name as city
    """
    waiqideke = neo4j_conn.query(waiqideke_query)
    
    return {
        "top_companies": companies,
        "city_distribution": cities,
        "waiqideke_cities": waiqideke
    }

# 启动事件
@app.on_event("shutdown")
def shutdown_event():
    neo4j_conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
