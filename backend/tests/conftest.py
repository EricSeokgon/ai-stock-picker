# 테스트 픽스처 정의 - 비동기 DB 세션 및 testcontainers 연동
import pytest
import pytest_asyncio

# Docker 가용성 확인 - testcontainers는 Docker가 필요
try:
    import docker
    docker_client = docker.from_env()
    docker_client.ping()
    DOCKER_AVAILABLE = True
except Exception:
    DOCKER_AVAILABLE = False

# asyncpg 가용성 확인
try:
    import asyncpg  # noqa: F401
    ASYNCPG_AVAILABLE = True
except ImportError:
    ASYNCPG_AVAILABLE = False


@pytest.fixture(scope="session")
def db_engine():
    """
    테스트용 비동기 PostgreSQL 엔진 생성 픽스처.
    testcontainers로 임시 PostgreSQL 인스턴스를 기동한다.
    Docker가 없으면 테스트를 건너뜀.
    """
    if not DOCKER_AVAILABLE:
        pytest.skip("Docker가 없어서 DB 통합 테스트를 건너뜁니다")
    if not ASYNCPG_AVAILABLE:
        pytest.skip("asyncpg가 설치되지 않아 DB 통합 테스트를 건너뜁니다")

    from testcontainers.postgres import PostgresContainer
    from sqlalchemy.ext.asyncio import create_async_engine
    from stock_picker.db.base import Base
    from stock_picker.db import models  # noqa: F401 - 모델 등록

    import asyncio

    with PostgresContainer("postgres:16-alpine") as postgres:
        # asyncpg 연결 문자열로 변환
        sync_url = postgres.get_connection_url()
        async_url = sync_url.replace("postgresql://", "postgresql+asyncpg://").replace(
            "psycopg2", "asyncpg"
        )

        engine = create_async_engine(async_url, echo=False)

        # 테이블 생성
        async def create_tables():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        asyncio.get_event_loop().run_until_complete(create_tables())

        yield engine

        # 정리
        async def dispose():
            await engine.dispose()

        asyncio.get_event_loop().run_until_complete(dispose())


@pytest_asyncio.fixture
async def db_session(db_engine):
    """
    각 테스트마다 독립적인 비동기 세션 제공.
    테스트 완료 후 롤백하여 격리성을 보장한다.
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    async with db_engine.begin() as conn:
        # 중첩 트랜잭션(savepoint)으로 각 테스트 격리
        async with AsyncSession(bind=conn, expire_on_commit=False) as session:
            yield session
            # 테스트 완료 후 롤백 (데이터 격리)
            await session.rollback()
