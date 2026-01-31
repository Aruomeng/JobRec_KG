"""
学生服务 - 用户相关路由
包含：登录、个人信息、技能诊断、课程管理
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Optional

from ..models import (
    LoginRequest,
    UpdateProfileRequest,
    SaveCoursesRequest,
    CoursePathRequest,
    SkillDiagnosisRequest
)
from ..utils import verify_password, get_password_hash
from ..dependencies import get_neo4j

router = APIRouter(prefix="/api/student", tags=["user"])

neo4j_conn = get_neo4j()


@router.post("/login")
def student_login(request: LoginRequest):
    """学生登录/注册"""
    query = """
    MATCH (s:Student {username: $username})
    OPTIONAL MATCH (s)-[:HAS_SKILL]->(sk:Skill)
    OPTIONAL MATCH (s)-[:ENROLLED_IN]->(c:Course)
    RETURN s.student_id AS student_id, s.name AS name, s.password AS password, 
           s.education AS education, s.major AS major, s.expected_position AS expected_position,
           COLLECT(DISTINCT sk.name) AS skills, COLLECT(DISTINCT c.name) AS courses
    """
    
    results = neo4j_conn.query(query, parameters={"username": request.username})
    
    if not results or results[0].get("student_id") is None:
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
    
    if stored_password:
        if not verify_password(request.password, stored_password):
            raise HTTPException(status_code=401, detail="Incorrect password")
    else:
        hashed_password = get_password_hash(request.password)
        neo4j_conn.query(
            "MATCH (s:Student {student_id: $student_id}) SET s.password = $password",
            parameters={"student_id": student["student_id"], "password": hashed_password}
        )
    
    return {"code": 200, "data": student}


@router.post("/parse-resume")
def upload_resume(file: UploadFile = File(...)):
    """简历解析"""
    skills = ["Python", "Java", "SQL", "数据分析"]
    return {"skills": skills, "message": "Resume parsed successfully"}


@router.post("/course-path")
def plan_course_path(request: CoursePathRequest):
    """课程规划"""
    query = """
    MATCH (j:Job {job_id: $target_job_id})-[:REQUIRES_SKILL]->(sk:Skill)<-[:TEACHES]-(c:Course)
    RETURN c.name AS name, c.course_id AS course_id, COLLECT(sk.name) AS covers
    ORDER BY SIZE(covers) DESC
    """
    results = neo4j_conn.query(query, parameters={"target_job_id": request.target_job_id})
    return {"course_path": results}


@router.get("/get-profile/{student_id}")
def get_profile(student_id: str):
    """获取用户完整信息"""
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


@router.post("/update-profile")
def update_profile(request: UpdateProfileRequest):
    """更新个人信息"""
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
    
    delete_skills_query = """
    MATCH (s:Student {student_id: $student_id})-[r:HAS_SKILL]->()
    DELETE r
    """
    neo4j_conn.query(delete_skills_query, parameters={"student_id": request.student_id})
    
    if request.skills:
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
    
    if hasattr(request, 'courses') and request.courses:
        delete_courses_query = """
        MATCH (s:Student {student_id: $student_id})-[r:ENROLLED_IN]->()
        DELETE r
        """
        neo4j_conn.query(delete_courses_query, parameters={"student_id": request.student_id})
        
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


@router.get("/courses")
def get_courses(major: Optional[str] = None):
    """获取可选课程列表"""
    if major:
        major_query = """
        MATCH (c:Course)
        WHERE c.major = $major OR c.department = $major
        OPTIONAL MATCH (c)-[:TEACHES_SKILL]->(sk:Skill)
        WITH c, COLLECT(DISTINCT sk.name) AS skills
        RETURN c.name AS name, SIZE(skills) AS skill_count, skills
        ORDER BY skill_count DESC
        LIMIT 50
        """
        results = neo4j_conn.query(major_query, parameters={"major": major})
        if results:
            return {"courses": results}
    
    popular_query = """
    MATCH (c:Course)
    OPTIONAL MATCH (s:Student)-[:TAKES]->(c)
    OPTIONAL MATCH (c)-[:TEACHES_SKILL]->(sk:Skill)
    WITH c, COUNT(DISTINCT s) AS student_count, COLLECT(DISTINCT sk.name) AS skills
    RETURN c.name AS name, student_count, SIZE(skills) AS skill_count, skills
    ORDER BY student_count DESC
    LIMIT 50
    """
    courses = neo4j_conn.query(popular_query)
    return {"courses": courses}


@router.post("/save-courses")
def save_courses(request: SaveCoursesRequest):
    """保存学生课程选择"""
    delete_query = """
    MATCH (s:Student {student_id: $student_id})-[r:TAKES]->()
    DELETE r
    """
    neo4j_conn.query(delete_query, parameters={"student_id": request.student_id})
    
    if request.courses:
        add_query = """
        MATCH (s:Student {student_id: $student_id})
        UNWIND $courses AS course_name
        MATCH (c:Course {name: course_name})
        MERGE (s)-[:TAKES]->(c)
        RETURN count(*) AS added
        """
        neo4j_conn.query(add_query, parameters={
            "student_id": request.student_id,
            "courses": request.courses
        })
    
    return {"message": "Courses saved successfully", "courses": request.courses}


@router.post("/skill-diagnosis")
def diagnose_skills(request: SkillDiagnosisRequest):
    """技能诊断：个性化职业导向的技能分析"""
    student_id = request.student_id
    
    # 获取用户基本信息
    profile_query = """
    MATCH (s:Student {student_id: $student_id})
    RETURN s.expected_position AS expected_position, s.education AS education, s.major AS major
    """
    profile_result = neo4j_conn.query(profile_query, parameters={"student_id": student_id})
    expected_position = profile_result[0]["expected_position"] if profile_result else None
    education = profile_result[0]["education"] if profile_result else None
    major = profile_result[0]["major"] if profile_result else None
    
    # 获取技能
    skills_query = """
    OPTIONAL MATCH (s:Student {student_id: $student_id})-[:HAS_SKILL]->(sk1:Skill)
    WITH COLLECT(DISTINCT sk1.name) AS direct_skills
    OPTIONAL MATCH (s2:Student {student_id: $student_id})-[:TAKES]->(c:Course)-[:TEACHES_SKILL]->(sk2:Skill)
    WITH direct_skills, COLLECT(DISTINCT sk2.name) AS course_skills
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
    
    # 期望职业技能分析
    position_skills = []
    if expected_position:
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
    
    # 市场热门技能分析
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
    
    # 同行对比
    def build_peer_query(where_clause):
        return f"""
        MATCH (s:Student)
        WHERE {where_clause} AND s.student_id <> $student_id
        OPTIONAL MATCH (s)-[:HAS_SKILL]->(sk1:Skill)
        OPTIONAL MATCH (s)-[:TAKES]->(:Course)-[:TEACHES_SKILL]->(sk2:Skill)
        WITH s, COLLECT(DISTINCT sk1.name) + COLLECT(DISTINCT sk2.name) AS all_skill_names
        WITH s, [x IN all_skill_names WHERE x IS NOT NULL | x] AS skills
        WITH s, SIZE(skills) AS skill_count, skills
        WITH COLLECT(skill_count) AS all_counts, COLLECT(skills) AS all_skills_lists
        UNWIND all_skills_lists AS skill_list
        UNWIND skill_list AS skill
        WITH all_counts, skill, COUNT(*) AS freq
        ORDER BY freq DESC
        WITH all_counts, COLLECT(skill)[0..5] AS top_skills
        WITH top_skills, 
             CASE WHEN SIZE(all_counts) > 0 THEN REDUCE(sum=0.0, x IN all_counts | sum + x) / SIZE(all_counts) ELSE 0 END AS avg_count,
             SIZE(all_counts) AS peer_count
        RETURN avg_count, peer_count, top_skills
        """
    
    peer_data = None
    
    if expected_position:
        peer_query = build_peer_query("s.expected_position = $position")
        peer_result = neo4j_conn.query(peer_query, parameters={"position": expected_position, "student_id": student_id})
        if peer_result and peer_result[0]["peer_count"] > 0:
            peer_data = peer_result[0]
    
    if not peer_data and major:
        peer_query = build_peer_query("s.major = $major")
        peer_result = neo4j_conn.query(peer_query, parameters={"major": major, "student_id": student_id})
        if peer_result and peer_result[0]["peer_count"] > 0:
            peer_data = peer_result[0]
    
    if not peer_data and education:
        peer_query = build_peer_query("s.education = $education")
        peer_result = neo4j_conn.query(peer_query, parameters={"education": education, "student_id": student_id})
        if peer_result and peer_result[0]["peer_count"] > 0:
            peer_data = peer_result[0]
    
    if not peer_data:
        peer_query = build_peer_query("s.student_id IS NOT NULL")
        peer_result = neo4j_conn.query(peer_query, parameters={"student_id": student_id})
        if peer_result and peer_result[0]["peer_count"] > 0:
            peer_data = peer_result[0]
    
    if peer_data:
        avg_skills_count = round(peer_data["avg_count"], 1)
        top_skills_in_peers = [s for s in peer_data["top_skills"] if s][:5]
        your_count = len(all_skills)
        rank_percentile = min(100, round(your_count / max(avg_skills_count, 1) * 50, 0))
    else:
        avg_skills_count = 0
        top_skills_in_peers = []
        rank_percentile = 50
    
    # 推荐课程
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
    
    # 生成诊断结论
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
