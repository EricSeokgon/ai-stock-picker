# 인증 관련 Pydantic v2 스키마
from pydantic import BaseModel, EmailStr


class UserRegister(BaseModel):
    """회원가입 요청 스키마"""
    # 사용자명: 3~50자 제한
    username: str
    email: EmailStr
    # 비밀번호: 최소 8자
    password: str


class UserLogin(BaseModel):
    """로그인 요청 스키마"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """토큰 응답 스키마 — access + refresh 쌍"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """JWT 페이로드 스키마"""
    # sub: 사용자명 (username)
    sub: str
    exp: int


class UserResponse(BaseModel):
    """사용자 정보 응답 스키마 (비밀번호 제외)"""
    id: int
    username: str
    email: str
    is_active: bool

    model_config = {"from_attributes": True}


class RefreshRequest(BaseModel):
    """refresh 토큰 갱신 요청"""
    refresh_token: str
