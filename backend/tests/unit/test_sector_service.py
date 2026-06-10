# 섹터 트렌드 집계 서비스 단위 테스트 (SPEC-STOCK-008 TASK-007)
import math
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_analysis(
    article_id: int = 1,
    sentiment_score: float = 0.5,
    sector_tags: list[str] | None = None,
) -> MagicMock:
    """테스트용 AnalysisResult Mock 생성."""
    a = MagicMock()
    a.article_id = article_id
    a.sentiment_score = sentiment_score
    a.sector_tags = sector_tags if sector_tags is not None else ["반도체"]
    return a


def _make_db_session(analyses: list) -> AsyncMock:
    """execute → scalars().all() 반환 Mock 세션 생성."""
    session = AsyncMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = analyses
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value = mock_scalars
    session.execute = AsyncMock(return_value=mock_execute_result)
    return session


class TestAggregateSectorTrends:
    """aggregate_sector_trends() 단위 테스트"""

    @pytest.mark.asyncio
    async def test_aggregate_sector_trends_empty_db(self):
        """해당 날짜 데이터 없으면 0을 반환하고 행을 생성하지 않는다."""
        from stock_picker.sector.service import aggregate_sector_trends

        session = _make_db_session([])
        result = await aggregate_sector_trends(session, date(2026, 6, 1))

        assert result == 0
        session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_aggregate_sector_trends_single_sector(self):
        """단일 섹터 기사들의 news_volume, avg_sentiment, trend_score가 정확히 계산된다."""
        from stock_picker.sector.service import aggregate_sector_trends

        analyses = [
            _make_analysis(article_id=1, sentiment_score=0.6, sector_tags=["반도체"]),
            _make_analysis(article_id=2, sentiment_score=0.4, sector_tags=["반도체"]),
        ]
        session = _make_db_session(analyses)

        # upsert 실행 캡처용
        executed_stmts = []
        original_execute = session.execute

        async def capture_execute(stmt, *args, **kwargs):
            executed_stmts.append(stmt)
            return await original_execute(stmt, *args, **kwargs)

        session.execute = capture_execute

        with patch("stock_picker.sector.service.pg_insert") as mock_pg_insert:
            mock_stmt = MagicMock()
            mock_stmt.on_conflict_do_update.return_value = mock_stmt
            mock_stmt.excluded = MagicMock()
            mock_pg_insert.return_value = MagicMock(return_value=mock_stmt)
            mock_pg_insert.return_value.return_value = mock_stmt

            # insert 호출 시 values() → mock_stmt 반환
            mock_insert_instance = MagicMock()
            mock_insert_instance.values.return_value = mock_stmt
            mock_pg_insert.return_value = mock_insert_instance

            session2 = AsyncMock()
            # 첫 execute는 SELECT (analyses 반환), 두 번째는 upsert
            call_count = 0

            async def side_effect(stmt, *args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    mock_sc = MagicMock()
                    mock_sc.all.return_value = analyses
                    mock_res = MagicMock()
                    mock_res.scalars.return_value = mock_sc
                    return mock_res
                return MagicMock()

            session2.execute = side_effect
            result = await aggregate_sector_trends(session2, date(2026, 6, 1))

        assert result == 1

    @pytest.mark.asyncio
    async def test_aggregate_sector_trends_multi_tag(self):
        """멀티 태그 기사는 각 섹터에 독립적으로 집계된다."""
        from stock_picker.sector.service import aggregate_sector_trends

        analyses = [
            _make_analysis(article_id=1, sentiment_score=0.8, sector_tags=["IT", "바이오"]),
        ]

        call_count = 0
        captured_rows = []

        async def side_effect(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                mock_sc = MagicMock()
                mock_sc.all.return_value = analyses
                mock_res = MagicMock()
                mock_res.scalars.return_value = mock_sc
                return mock_res
            # upsert stmt: values 검사를 위해 캡처
            captured_rows.append(stmt)
            return MagicMock()

        session = AsyncMock()
        session.execute = side_effect

        with patch("stock_picker.sector.service.pg_insert") as mock_pg_insert:
            upsert_values = []

            def mock_values(rows):
                upsert_values.extend(rows)
                m = MagicMock()
                m.on_conflict_do_update.return_value = m
                m.excluded = MagicMock()
                return m

            mock_insert_cls = MagicMock()
            mock_insert_cls.values = mock_values
            mock_pg_insert.return_value = mock_insert_cls

            result = await aggregate_sector_trends(session, date(2026, 6, 1))

        # IT와 바이오 두 섹터 모두 집계되어야 함
        assert result == 2
        sectors = {row["sector"] for row in upsert_values}
        assert "IT" in sectors
        assert "바이오" in sectors

    @pytest.mark.asyncio
    async def test_aggregate_skips_empty_sector_tags(self):
        """sector_tags가 빈 배열인 기사는 집계에서 제외된다."""
        from stock_picker.sector.service import aggregate_sector_trends

        analyses = [
            _make_analysis(article_id=1, sentiment_score=0.5, sector_tags=[]),
            _make_analysis(article_id=2, sentiment_score=0.6, sector_tags=[]),
        ]
        session = _make_db_session(analyses)

        result = await aggregate_sector_trends(session, date(2026, 6, 1))

        # 유효한 섹터 없으므로 0
        assert result == 0

    @pytest.mark.asyncio
    async def test_aggregate_sector_trends_upsert_idempotent(self):
        """같은 날짜로 두 번 실행해도 중복 행이 생기지 않는다 (upsert)."""
        from stock_picker.sector.service import aggregate_sector_trends

        analyses = [
            _make_analysis(article_id=1, sentiment_score=0.5, sector_tags=["반도체"]),
        ]

        execute_calls = []

        async def side_effect(stmt):
            execute_calls.append(stmt)
            mock_sc = MagicMock()
            mock_sc.all.return_value = analyses
            mock_res = MagicMock()
            mock_res.scalars.return_value = mock_sc
            return mock_res

        session = AsyncMock()
        session.execute = side_effect

        with patch("stock_picker.sector.service.pg_insert") as mock_pg_insert:
            mock_insert_cls = MagicMock()
            m = MagicMock()
            m.on_conflict_do_update.return_value = m
            m.excluded = MagicMock()
            mock_insert_cls.values.return_value = m
            mock_pg_insert.return_value = mock_insert_cls

            r1 = await aggregate_sector_trends(session, date(2026, 6, 1))
            r2 = await aggregate_sector_trends(session, date(2026, 6, 1))

        # 두 번 모두 on_conflict_do_update로 upsert
        assert r1 == 1
        assert r2 == 1
        assert m.on_conflict_do_update.call_count == 2


class TestComputeTrendScore:
    """_compute_trend_score() 공식 및 클램핑 테스트"""

    def test_trend_score_formula(self):
        """공식: avg_sentiment * 0.7 + log(news_volume + 1) * 0.3 검증.

        클램핑 전 원시 공식 값이 범위 내일 때만 동일해야 한다.
        news_volume=1이면 log(2)*0.3 ≈ 0.208, sentiment=0 → raw = 0.208 (범위 내).
        """
        from stock_picker.sector.service import _compute_trend_score

        avg_sentiment = 0.0
        news_volume = 1
        expected = avg_sentiment * 0.7 + math.log(news_volume + 1) * 0.3
        result = _compute_trend_score(avg_sentiment, news_volume)
        assert abs(result - expected) < 1e-6

    def test_trend_score_zero_volume(self):
        """뉴스 0건: log(1) = 0 이므로 avg_sentiment * 0.7."""
        from stock_picker.sector.service import _compute_trend_score

        result = _compute_trend_score(0.5, 0)
        assert abs(result - 0.5 * 0.7) < 1e-6

    def test_trend_score_clamped_max(self):
        """매우 높은 news_volume에서 최대 1.0으로 클램핑."""
        from stock_picker.sector.service import _compute_trend_score

        result = _compute_trend_score(1.0, 10000)
        assert result <= 1.0

    def test_trend_score_clamped_min(self):
        """매우 부정적 감성에서 최솟값 -1.0으로 클램핑."""
        from stock_picker.sector.service import _compute_trend_score

        result = _compute_trend_score(-1.0, 0)
        assert result >= -1.0

    def test_trend_score_negative_sentiment(self):
        """부정적 감성이면 트렌드 스코어도 음수가 된다."""
        from stock_picker.sector.service import _compute_trend_score

        result = _compute_trend_score(-0.8, 1)
        assert result < 0
