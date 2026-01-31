"""
学生服务 - 数据模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict


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


class FavoriteRequest(BaseModel):
    """收藏职位请求"""
    user_id: str
    job_id: str
    job_title: Optional[str] = None
    company: Optional[str] = None
    salary: Optional[str] = None
    city: Optional[str] = None
