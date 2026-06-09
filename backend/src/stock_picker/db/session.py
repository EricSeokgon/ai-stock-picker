# 비동기 데이터베이스 세션 관리
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# 환경변수에서 DB URL 로드 (테스트 시 재정의 가능)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://stock_picker:stock_picker@localhost:5432/stock_picker",
)

# 비동기 엔진 생성 - 연결 풀 설정 포함
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # 연결 유효성 자동 검사
)

# 세션 팩토리 - FastAPI 의존성 주입용
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 커밋 후 객체 만료 방지
)


# 동기 세션 팩토리 — auth 라우터 전용 (TestClient와 호환)
# @MX:NOTE: [AUTO] 비동기 엔진과 별도로 동기 세션을 사용하는 이유:
# auth 라우터는 TestClient(동기)로 테스트하며, asyncpg는 동기 연결을 지원하지 않음
_SYNC_DATABASE_URL = DATABASE_URL.replace("+asyncpg", "")
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker as _sessionmaker

    _sync_engine = create_engine(
        _SYNC_DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )
    SyncSessionLocal = _sessionmaker(autocommit=False, autoflush=False, bind=_sync_engine)
except Exception:
    # 테스트 환경에서는 호출부에서 override하므로 None 허용
    SyncSessionLocal = None  # type: ignore[assignment]


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 의존성 주입용 세션 생성기"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
