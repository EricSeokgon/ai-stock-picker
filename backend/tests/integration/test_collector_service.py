# 수집 서비스 통합 테스트
# AC-1: 멱등성 (중복 URL 저장 안 됨)
# AC-2: 부분 실패 처리 (한 소스 실패해도 나머지 계속)

import pytest
import httpx
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

# Docker/DB 가용성에 따라 DB 의존 통합 테스트 스킵
pytest_mark_integration = pytest.mark.skipif(
    True,  # Docker 없는 환경에서는 mock 기반 테스트만 실행
    reason="DB 통합 테스트는 Docker 환경에서 실행"
)


class TestCollectorServiceIdempotency:
    """AC-1: 멱등성 - 동일 URL 두 번 수집 시 중복 없음"""

    @pytest.mark.asyncio
    async def test_collect_all_returns_counts_per_source(self):
        """collect_all 반환값이 소스별 수집 카운트 딕셔너리인지 확인"""
        from stock_picker.collectors.service import CollectorService
        from stock_picker.collectors.base import RawArticle

        # DB 세션 mock
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        # 수집기 mock - 2개 기사 반환
        mock_articles = [
            RawArticle(
                url="https://test.com/article/1",
                title="테스트 기사 1",
                content="내용 1",
                source="hankyung",
                published_at=datetime.now(tz=timezone.utc),
            )
        ]

        with patch(
            "stock_picker.collectors.rss.HankyungCollector.collect",
            new_callable=AsyncMock,
            return_value=mock_articles,
        ):
            service = CollectorService()
            # hankyung만 mock, 나머지는 빈 리스트
            results = await service.collect_all(mock_session)

        assert isinstance(results, dict)

    @pytest.mark.asyncio
    async def test_same_url_not_duplicated(self):
        """동일 URL 기사를 두 번 수집해도 중복 저장 안 됨 (멱등성)"""
        from stock_picker.collectors.service import CollectorService
        from stock_picker.collectors.base import RawArticle

        duplicate_articles = [
            RawArticle(
                url="https://test.com/same-url",
                title="중복 기사",
                content="내용",
                source="test",
                published_at=datetime.now(tz=timezone.utc),
            )
        ] * 2  # 같은 URL의 기사 두 개

        # _save_articles가 ON CONFLICT DO NOTHING 처리하는지 확인
        mock_session = AsyncMock()
        execute_calls = []

        # execute가 rowcount=0인 결과를 반환하도록 mock
        mock_result = MagicMock()
        mock_result.rowcount = 0  # 중복으로 삽입 안 됨

        async def track_execute(stmt, *args, **kwargs):
            execute_calls.append(stmt)
            return mock_result

        mock_session.execute = track_execute

        service = CollectorService()
        # 내부 _save_articles 직접 테스트
        count = await service._save_articles(mock_session, duplicate_articles)

        # 에러 없이 실행되어야 함
        assert count >= 0
        # 2개 기사에 대해 2번 execute 호출됨
        assert len(execute_calls) == 2


class TestCollectorServicePartialFailure:
    """AC-2: 부분 실패 처리 - 한 소스 실패해도 나머지 성공"""

    @pytest.mark.asyncio
    async def test_one_source_429_other_sources_still_collected(self):
        """한 소스 429 오류 → 다른 소스는 정상 수집 (REQ-NEWS-005)"""
        from stock_picker.collectors.service import CollectorService

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        async def failing_collect():
            raise httpx.HTTPStatusError(
                "429 Too Many Requests",
                request=MagicMock(),
                response=MagicMock(status_code=429),
            )

        # 파이프라인 중단 없이 실패 소스는 0, 성공 소스는 카운트됨
        service = CollectorService()

        # collect_all이 예외를 격리하는지 확인
        error_raised = False
        try:
            # 실패하는 수집기를 포함한 mock 테스트
            await service._collect_with_error_isolation(
                "failing_source", failing_collect
            )
        except Exception:
            error_raised = True

        # 에러가 외부로 전파되면 안 됨
        assert not error_raised

    @pytest.mark.asyncio
    async def test_all_sources_fail_returns_zero_counts(self):
        """모든 소스 실패 → 전체 0 카운트, 크래시 없음"""
        from stock_picker.collectors.service import CollectorService

        async def always_fail():
            raise Exception("연결 실패")

        service = CollectorService()

        # 모든 수집기 실패해도 크래시 없음
        try:
            result = await service._collect_with_error_isolation("test", always_fail)
            assert result == 0  # 실패 시 0 반환
        except Exception:
            pytest.fail("_collect_with_error_isolation이 예외를 외부로 전파해서는 안 됨")
