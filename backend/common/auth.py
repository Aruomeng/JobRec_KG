"""
认证模块 - Supabase集成
"""
from fastapi import HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime, timedelta
import jwt
from pydantic import BaseModel
from . import config
from .database import get_supabase_client

security = HTTPBearer(auto_error=False)

class UserRole:
    STUDENT = "student"
    ENTERPRISE = "enterprise"
    UNIVERSITY = "university"

class TokenData(BaseModel):
    user_id: str
    email: str
    role: str
    exp: datetime

class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str
    role: str  # student / enterprise / university

class LoginRequest(BaseModel):
    email: str
    password: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    role: str
    display_name: str

def create_access_token(user_id: str, email: str, role: str) -> str:
    """创建JWT访问令牌"""
    expire = datetime.utcnow() + timedelta(hours=config.JWT_EXPIRE_HOURS)
    payload = {
        "user_id": user_id,
        "email": email,
        "role": role,
        "exp": expire
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)

def verify_token(token: str) -> TokenData:
    """验证JWT令牌"""
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        return TokenData(**payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="令牌已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="无效令牌")

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[TokenData]:
    """获取当前登录用户"""
    if credentials is None:
        return None
    return verify_token(credentials.credentials)

async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """要求用户登录"""
    if credentials is None:
        raise HTTPException(status_code=401, detail="未登录")
    return verify_token(credentials.credentials)

def require_role(allowed_roles: list[str]):
    """要求特定角色"""
    async def role_checker(user: TokenData = Depends(require_auth)) -> TokenData:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="权限不足")
        return user
    return role_checker

async def register_user(request: RegisterRequest) -> AuthResponse:
    """用户注册"""
    supabase = get_supabase_client()
    if not supabase:
        raise HTTPException(status_code=500, detail="认证服务未配置")
    
    try:
        # 使用Supabase注册
        auth_response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password,
            "options": {
                "data": {
                    "display_name": request.display_name,
                    "role": request.role
                }
            }
        })
        
        if auth_response.user is None:
            raise HTTPException(status_code=400, detail="注册失败")
        
        user_id = auth_response.user.id
        
        # 创建用户档案
        supabase.table("user_profiles").insert({
            "id": user_id,
            "role": request.role,
            "display_name": request.display_name
        }).execute()
        
        # 创建JWT令牌
        token = create_access_token(user_id, request.email, request.role)
        
        return AuthResponse(
            access_token=token,
            user_id=user_id,
            email=request.email,
            role=request.role,
            display_name=request.display_name
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

async def login_user(request: LoginRequest, expected_role: Optional[str] = None) -> AuthResponse:
    """用户登录"""
    supabase = get_supabase_client()
    if not supabase:
        raise HTTPException(status_code=500, detail="认证服务未配置")
    
    try:
        # 使用Supabase登录
        auth_response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if auth_response.user is None:
            raise HTTPException(status_code=401, detail="邮箱或密码错误")
        
        user_id = auth_response.user.id
        user_metadata = auth_response.user.user_metadata or {}
        role = user_metadata.get("role", "student")
        display_name = user_metadata.get("display_name", "")
        
        # 检查角色
        if expected_role and role != expected_role:
            raise HTTPException(status_code=403, detail=f"请使用{expected_role}端登录")
        
        # 创建JWT令牌
        token = create_access_token(user_id, request.email, role)
        
        return AuthResponse(
            access_token=token,
            user_id=user_id,
            email=request.email,
            role=role,
            display_name=display_name
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
