# 배치 분석 워커 테스트 (TASK-022)
# REQ-AI-004: BATCH_SIZE 기사를 단일 Claude 호출로 묶음
import math
from unittest.mock import AsyncMock, MagicMock

import pytest

from stock_picker.analysis.schema import ClaudeAnalysisOutput


def make_mock_article(article_id: int, title: str = "테스트") -> MagicMock:
    """테스트용 Mock Article 생성 헬퍼."""
    article = MagicMock()
    article.id = article_id
    article.title = title
    article.content = "테스트 본문"
    article.status = "collected"
    return article


def make_mock_output() -> ClaudeAnalysisOutput:
    """테스트용 Mock 분석 결과 생성 헬퍼."""
    return ClaudeAnalysisOutput(
        sentiment="positive",
        sentiment_score=0.7,
        sector_tags=["IT"],
        keywords=["테스트"],
        summary="요약",
    )


class TestBatchProcessing:
    """배치 처리 테스트 - Claude API 호출 횟수 최소화"""

    @pytest.mark.asyncio
    async def test_10_articles_calls_ceil_10_div_batch_size_times(self):
        """10개 기사는 ceil(10/BATCH_SIZE)번 Claude를 호출해야 한다"""
        from stock_picker.analysis.worker import AnalysisWorker, BATCH_SIZE

        articles = [make_mock_article(i) for i in range(1, 11)]

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        # 배치 분석 메서드 mock
        expected_calls = math.ceil(10 / BATCH_SIZE)
        batch_outputs = [make_mock_output() for _ in range(BATCH_SIZE)]

        mock_claude = AsyncMock()
        mock_claude.analyze_batch = AsyncMock(return_value=batch_outputs)

        worker = AnalysisWorker(client=mock_claude)
        worker._get_unanalyzed = AsyncMock(return_value=articles)
        worker._save_analysis = AsyncMock()

        await worker.run_batch(mock_session)

        assert mock_claude.analyze_batch.call_count == expected_calls

    @pytest.mark.asyncio
    async def test_5_articles_with_batch_size_5_calls_once(self):
        """5개 기사는 BATCH_SIZE=5일 때 1번만 호출해야 한다"""
        from stock_picker.analysis.worker import AnalysisWorker, BATCH_SIZE

        if BATCH_SIZE != 5:
            pytest.skip("BATCH_SIZE가 5가 아닌 경우 이 테스트 건너뜀")

        articles = [make_mock_article(i) for i in range(1, 6)]

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_claude = AsyncMock()
        mock_claude.analyze_batch = AsyncMock(
            return_value=[make_mock_output() for _ in range(5)]
        )

        worker = AnalysisWorker(client=mock_claude)
        worker._get_unanalyzed = AsyncMock(return_value=articles)
        worker._save_analysis = AsyncMock()

        await worker.run_batch(mock_session)

        mock_claude.analyze_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_batch_failure_falls_back_to_individual(self):
        """배치 실패 시 개별 처리로 폴백해야 한다 (부분 실패 격리)"""
        from stock_picker.analysis.worker import AnalysisWorker

        articles = [make_mock_article(i) for i in range(1, 4)]

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_claude = AsyncMock()
        # analyze_batch는 항상 실패
        mock_claude.analyze_batch = AsyncMock(return_value=None)
        # 개별 analyze는 성공
        mock_claude.analyze = AsyncMock(return_value=make_mock_output())

        worker = AnalysisWorker(client=mock_claude)
        worker._get_unanalyzed = AsyncMock(return_value=articles)
        worker._save_analysis = AsyncMock()

        results = await worker.run_batch(mock_session)

        # 폴백 후 개별 처리로 모두 성공해야 함
        assert results["analyzed"] == 3
        assert results["failed"] == 0

    @pytest.mark.asyncio
    async def test_batch_results_match_article_count(self):
        """배치 처리 결과 수는 기사 수와 일치해야 한다"""
        from stock_picker.analysis.worker import AnalysisWorker

        articles = [make_mock_article(i) for i in range(1, 8)]

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_claude = AsyncMock()
        mock_claude.analyze_batch = AsyncMock(
            return_value=[make_mock_output() for _ in range(5)]  # BATCH_SIZE만큼
        )

        worker = AnalysisWorker(client=mock_claude)
        worker._get_unanalyzed = AsyncMock(return_value=articles)
        worker._save_analysis = AsyncMock()

        results = await worker.run_batch(mock_session)

        # 분석된 총 수 = 기사 수
        assert results["analyzed"] + results["failed"] == 7

    @pytest.mark.asyncio
    async def test_empty_articles_returns_zero_counts(self):
        """기사 없으면 analyzed=0, failed=0 반환해야 한다"""
        from stock_picker.analysis.worker import AnalysisWorker

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        mock_claude = AsyncMock()

        worker = AnalysisWorker(client=mock_claude)
        worker._get_unanalyzed = AsyncMock(return_value=[])
        worker._save_analysis = AsyncMock()

        results = await worker.run_batch(mock_session)

        assert results["analyzed"] == 0
        assert results["failed"] == 0
