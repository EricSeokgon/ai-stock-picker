# 분석 워커 통합 테스트
# - 3개 기사 분석 완료 → status = 'analyzed'
# - Claude None 반환 시 → status = 'analysis_failed', 크래시 없음

import pytest
from unittest.mock import AsyncMock, MagicMock

from stock_picker.analysis.schema import ClaudeAnalysisOutput


def make_mock_article(
    article_id: int,
    title: str = "테스트 기사",
    content: str = "테스트 내용",
    status: str = "collected",
):
    """Mock Article 객체 생성 헬퍼"""
    article = MagicMock()
    article.id = article_id
    article.title = title
    article.content = content
    article.status = status
    return article


def make_mock_analysis_output():
    """Mock ClaudeAnalysisOutput 생성 헬퍼"""
    return ClaudeAnalysisOutput(
        sentiment="positive",
        sentiment_score=0.72,
        sector_tags=["반도체"],
        keywords=["삼성전자"],
        summary="삼성전자가 2분기 좋은 실적을 냈다.",
    )


class TestAnalysisWorkerSuccess:
    """워커 정상 처리 테스트"""

    @pytest.mark.asyncio
    async def test_worker_processes_collected_articles(self):
        """status='collected' 기사 3개 → Claude 분석 후 status='analyzed'"""
        from stock_picker.analysis.worker import AnalysisWorker

        # 3개의 미분석 기사
        articles = [make_mock_article(i) for i in range(1, 4)]

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        # Claude 클라이언트 mock
        mock_claude = AsyncMock()
        mock_claude.analyze = AsyncMock(return_value=make_mock_analysis_output())

        worker = AnalysisWorker(client=mock_claude)
        worker._get_unanalyzed = AsyncMock(return_value=articles)
        worker._save_analysis = AsyncMock()

        results = await worker.run(mock_session)

        assert results["analyzed"] == 3
        assert results["failed"] == 0

        # 각 기사 상태가 'analyzed'로 변경되었는지 확인
        for article in articles:
            assert article.status == "analyzed"

    @pytest.mark.asyncio
    async def test_worker_saves_analysis_for_each_article(self):
        """각 기사마다 analysis 저장 메서드 호출 확인"""
        from stock_picker.analysis.worker import AnalysisWorker

        articles = [make_mock_article(i) for i in range(1, 4)]

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_claude = AsyncMock()
        mock_claude.analyze = AsyncMock(return_value=make_mock_analysis_output())

        worker = AnalysisWorker(client=mock_claude)
        worker._get_unanalyzed = AsyncMock(return_value=articles)
        worker._save_analysis = AsyncMock()

        await worker.run(mock_session)

        # 3번 save_analysis 호출
        assert worker._save_analysis.call_count == 3

    @pytest.mark.asyncio
    async def test_worker_commits_session(self):
        """워커 실행 후 세션 커밋 확인"""
        from stock_picker.analysis.worker import AnalysisWorker

        articles = [make_mock_article(1)]

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_claude = AsyncMock()
        mock_claude.analyze = AsyncMock(return_value=make_mock_analysis_output())

        worker = AnalysisWorker(client=mock_claude)
        worker._get_unanalyzed = AsyncMock(return_value=articles)
        worker._save_analysis = AsyncMock()

        await worker.run(mock_session)

        mock_session.commit.assert_called_once()


class TestAnalysisWorkerFailure:
    """워커 실패 처리 테스트"""

    @pytest.mark.asyncio
    async def test_claude_returns_none_sets_analysis_failed_status(self):
        """Claude None 반환 → article.status = 'analysis_failed' (REQ-AI-005)"""
        from stock_picker.analysis.worker import AnalysisWorker

        article = make_mock_article(1)

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_claude = AsyncMock()
        mock_claude.analyze = AsyncMock(return_value=None)  # Claude 실패

        worker = AnalysisWorker(client=mock_claude)
        worker._get_unanalyzed = AsyncMock(return_value=[article])
        worker._save_analysis = AsyncMock()

        results = await worker.run(mock_session)

        assert results["failed"] == 1
        assert results["analyzed"] == 0
        assert article.status == "analysis_failed"

    @pytest.mark.asyncio
    async def test_one_failure_does_not_stop_other_articles(self):
        """한 기사 실패해도 나머지 계속 처리 (격리)"""
        from stock_picker.analysis.worker import AnalysisWorker

        articles = [make_mock_article(i) for i in range(1, 4)]

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        call_count = 0

        async def selective_fail(title, content):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # 두 번째 기사만 실패
                return None
            return make_mock_analysis_output()

        mock_claude = AsyncMock()
        mock_claude.analyze = selective_fail

        worker = AnalysisWorker(client=mock_claude)
        worker._get_unanalyzed = AsyncMock(return_value=articles)
        worker._save_analysis = AsyncMock()

        results = await worker.run(mock_session)

        assert results["analyzed"] == 2
        assert results["failed"] == 1

    @pytest.mark.asyncio
    async def test_no_crash_when_claude_returns_none(self):
        """Claude None 반환 시 파이프라인 크래시 없음"""
        from stock_picker.analysis.worker import AnalysisWorker

        articles = [make_mock_article(i) for i in range(1, 4)]

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_claude = AsyncMock()
        mock_claude.analyze = AsyncMock(return_value=None)  # 모두 실패

        worker = AnalysisWorker(client=mock_claude)
        worker._get_unanalyzed = AsyncMock(return_value=articles)
        worker._save_analysis = AsyncMock()

        # 예외 없이 실행되어야 함
        try:
            results = await worker.run(mock_session)
            assert results["failed"] == 3
        except Exception as e:
            pytest.fail(f"워커가 예외를 발생시켜서는 안 됨: {e}")
