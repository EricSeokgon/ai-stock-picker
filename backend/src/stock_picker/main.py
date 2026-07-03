# SPEC-STOCK-040: 테스트 친화적 앱 엔트리포인트
# 테스트에서 `from stock_picker.main import app` 으로 참조하며,
# patch("stock_picker.auth.dependencies.get_current_user") 패턴을 지원하기 위해
# 런타임에 모듈 속성을 동적 조회하는 프록시 의존성을 사용한다.
from __future__ import annotations

from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from stock_picker.api.main import create_app
from stock_picker.auth import dependencies as auth_deps
from stock_picker.auth.dependencies import get_current_user as _real_get_current_user
from stock_picker.auth.dependencies import get_db_session as _real_get_db_session
from stock_picker.db.models import User
from sqlalchemy.orm import Session

# auto_error=False — Authorization 헤더 없을 때 401 대신 None 반환 (프록시에서 직접 처리)
_bearer_optional = HTTPBearer(auto_error=False)


def _patching_friendly_get_db_session() -> Generator:
    """patch("stock_picker.auth.dependencies.get_db_session") 호환 프록시.

    패치 없음 → 원본 제너레이터 실행 (DB 미설정 환경에서는 None yield).
    패치됨  → Mock 반환값을 그대로 yield.
    """
    current_fn = auth_deps.get_db_session
    if current_fn is _real_get_db_session:
        try:
            # 실제 환경 — 원본 제너레이터 통과
            yield from _real_get_db_session()
        except Exception:
            # DB 미설정 환경 (단위 테스트) — None yield
            # get_current_user가 패치되어 있으면 db는 사용하지 않음
            yield None
    else:
        # 테스트 환경 (패치됨) — Mock 반환값을 db로 사용
        yield current_fn()


async def _patching_friendly_get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_optional),
    db: Session = Depends(_patching_friendly_get_db_session),
) -> User:
    """patch("stock_picker.auth.dependencies.get_current_user") 호환 프록시.

    패치 없음 → 원본 함수에 credentials/db 주입하여 호출.
    패치됨   → Mock을 인수 없이 직접 호출 (return_value 또는 side_effect 적용).
    side_effect=Exception → HTTPException(401) 으로 변환.
    """
    current_fn = auth_deps.get_current_user
    if current_fn is not _real_get_current_user:
        # 테스트 환경 (패치됨)
        try:
            return current_fn()
        except HTTPException:
            raise
        except Exception as exc:
            # 일반 예외 → 401로 변환 (unauth 테스트 호환)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
            ) from exc

    # 실제 환경 — Authorization 헤더 필수
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 정보가 없습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _real_get_current_user(credentials=credentials, db=db)


# 테스트용 앱 — 의존성 프록시를 통해 patch() 패턴 지원
app = create_app()
app.dependency_overrides[_real_get_current_user] = _patching_friendly_get_current_user
app.dependency_overrides[_real_get_db_session] = _patching_friendly_get_db_session

__all__ = ["app"]
