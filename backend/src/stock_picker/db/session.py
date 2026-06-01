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


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 의존성 주입용 세션 생성기"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
