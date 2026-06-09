# JWT 인증 서비스 — bcrypt 직접 사용 (passlib 제외)
# @MX:ANCHOR: [AUTO] 인증 핵심 서비스 — 라우터/의존성/스케줄러 훅에서 참조
# @MX:REASON: hash_password, verify_password, create_access_token이 3곳 이상에서 호출됨
import os
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from stock_picker.auth.schemas import TokenPayload

# JWT 설정값
# @MX:NOTE: [AUTO] SECRET_KEY는 운영환경에서 반드시 환경변수로 교체 필요
_SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
_ALGORITHM = "HS256"
_ACCESS_TOKEN_EXPIRE_MINUTES = 60        # access token: 1시간
_REFRESH_TOKEN_EXPIRE_DAYS = 7           # refresh token: 7일


def hash_password(password: str) -> str:
    """bcrypt로 비밀번호 해싱 (cost factor 12)

    passlib 대신 bcrypt 직접 사용 — 충돌 방지 결정.
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """bcrypt 비밀번호 검증"""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(data: dict) -> str:
    """JWT access token 생성 (1시간 만료)"""
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload["exp"] = expire
    return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """JWT refresh token 생성 (7일 만료)"""
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=_REFRESH_TOKEN_EXPIRE_DAYS)
    payload["exp"] = expire
    # refresh token 식별자 추가
    payload["type"] = "refresh"
    return jwt.encode(payload, _SECRET_KEY, algorithm=_ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    """JWT 토큰 검증 및 페이로드 반환.

    만료 또는 서명 오류 시 JWTError 발생.
    """
    # @MX:WARN: [AUTO] options를 수정하면 만료 검증이 무력화될 수 있음
    # @MX:REASON: verify_exp=False로 설정 시 만료된 토큰도 유효 처리됨
    decoded = jwt.decode(token, _SECRET_KEY, algorithms=[_ALGORITHM])
    return TokenPayload(sub=decoded["sub"], exp=decoded["exp"])
