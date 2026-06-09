# FastAPI JWT 인증 의존성 — Bearer 토큰 검증 후 사용자 반환
from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from stock_picker.auth.service import decode_token
from stock_picker.db.models import User

bearer_scheme = HTTPBearer(auto_error=True)


def get_db_session() -> Generator[Session, None, None]:
    """동기 DB 세션 의존성 — 테스트에서 override 가능.

    # @MX:ANCHOR: [AUTO] 인증 라우터 DB 세션 진입점
    # @MX:REASON: 테스트 격리를 위해 override 대상으로 설계; auth 라우터 모든 엔드포인트에서 사용
    """
    from stock_picker.db.session import SyncSessionLocal  # type: ignore[import]
    db: Session = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db_session),
) -> User:
    """Bearer 토큰 검증 → 현재 사용자 반환.

    토큰 오류 또는 사용자 미발견 시 401 반환.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보가 유효하지 않습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(credentials.credentials)
        username: str = payload.sub
    except (JWTError, KeyError):
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="비활성화된 계정입니다",
        )
    return user
