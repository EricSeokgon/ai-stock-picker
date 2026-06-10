# 섹터 랭킹/상세 API 통합 테스트 (SPEC-STOCK-008 TASK-007)
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _make_client_with_db(mock_session: AsyncMock) -> TestClient:
    """DB 세션 Override된 TestClient 반환."""
    from stock_picker.api.main import create_app
    from stock_picker.db.session import get_session

    async def override_get_session():
        yield mock_session

    app = create_app()
    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app)


def _make_sector_trend_row(
    sector: str = "반도체",
    trade_date: date | None = None,
    trend_score: float = 0.75,
    news_volume: int = 10,
    avg_sentiment: float = 0.5,
) -> MagicMock:
    """테스트용 SectorTrend Mock."""
    row = MagicMock()
    row.sector = sector
    row.trade_date = datetime.combine(
        trade_date or date(2026, 6, 1), datetime.min.time(), tzinfo=timezone.utc
    )
    row.trend_score = trend_score
    row.news_volume = news_volume
    row.avg_sentiment = avg_sentiment
    return row


def _make_session_with_sector_trends(rows: list) -> AsyncMock:
    """scalars().all() → rows 반환하는 Mock 세션."""
    session = AsyncMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = rows
    mock_execute_result = MagicMock()
    mock_execute_result.scalars.return_value = mock_scalars
    session.execute = AsyncMock(return_value=mock_execute_result)
    return session


class TestSectorRankingEndpoint:
    """GET /sectors/ranking 엔드포인트 테스트"""

    def test_get_sector_ranking_empty(self):
        """데이터 없으면 200과 빈 sectors 리스트를 반환한다."""
        session = _make_session_with_sector_trends([])
        client = _make_client_with_db(session)

        response = client.get("/sectors/ranking")

        assert response.status_code == 200
        body = response.json()
        assert body["sectors"] == []
        assert body["total"] == 0

    def test_get_sector_ranking_with_data(self):
        """데이터 있으면 정렬된 섹터 목록을 반환한다."""
        rows = [
            _make_sector_trend_row("반도체", trend_score=0.9),
            _make_sector_trend_row("IT", trend_score=0.5),
            _make_sector_trend_row("바이오", trend_score=0.7),
        ]
        session = _make_session_with_sector_trends(rows)
        client = _make_client_with_db(session)

        response = client.get("/sectors/ranking?sort=score&limit=10")

        assert response.status_code == 200
        body = response.json()
        assert len(body["sectors"]) == 3
        # 내림차순 정렬 확인 (반도체 > 바이오 > IT)
        sector_names = [s["sector"] for s in body["sectors"]]
        assert sector_names[0] == "반도체"

    def test_get_sector_ranking_sort_by_sentiment(self):
        """sort=sentiment 파라미터로 avg_sentiment 기준 정렬이 된다."""
        rows = [
            _make_sector_trend_row("반도체", avg_sentiment=0.3),
            _make_sector_trend_row("바이오", avg_sentiment=0.9),
        ]
        session = _make_session_with_sector_trends(rows)
        client = _make_client_with_db(session)

        response = client.get("/sectors/ranking?sort=sentiment")

        assert response.status_code == 200
        body = response.json()
        assert body["sort"] == "sentiment"
        # 바이오가 더 높은 sentiment이므로 첫 번째
        assert body["sectors"][0]["sector"] == "바이오"

    def test_get_sector_ranking_sort_by_volume(self):
        """sort=volume 파라미터로 news_volume 기준 정렬이 된다."""
        rows = [
            _make_sector_trend_row("반도체", news_volume=5),
            _make_sector_trend_row("IT", news_volume=20),
        ]
        session = _make_session_with_sector_trends(rows)
        client = _make_client_with_db(session)

        response = client.get("/sectors/ranking?sort=volume")

        assert response.status_code == 200
        body = response.json()
        assert body["sectors"][0]["sector"] == "IT"

    def test_get_sector_ranking_limit_respected(self):
        """limit 파라미터가 반환 개수를 제한한다."""
        rows = [
            _make_sector_trend_row(f"섹터{i}", trend_score=float(i) / 10)
            for i in range(5)
        ]
        session = _make_session_with_sector_trends(rows)
        client = _make_client_with_db(session)

        response = client.get("/sectors/ranking?limit=2")

        assert response.status_code == 200
        body = response.json()
        assert len(body["sectors"]) <= 2

    def test_get_sector_ranking_response_schema(self):
        """응답 스키마에 필수 필드가 포함되어야 한다."""
        rows = [_make_sector_trend_row("반도체")]
        session = _make_session_with_sector_trends(rows)
        client = _make_client_with_db(session)

        response = client.get("/sectors/ranking")

        assert response.status_code == 200
        body = response.json()
        assert "sort" in body
        assert "limit" in body
        assert "sectors" in body
        assert "total" in body
        if body["sectors"]:
            item = body["sectors"][0]
            assert {"sector", "trade_date", "news_volume", "avg_sentiment", "trend_score"}.issubset(item.keys())


class TestSectorDetailEndpoint:
    """GET /sectors/{sector}/detail 엔드포인트 테스트"""

    def test_get_sector_detail_not_found(self):
        """데이터 없으면 404와 한국어 오류 메시지를 반환한다."""
        session = _make_session_with_sector_trends([])
        client = _make_client_with_db(session)

        response = client.get("/sectors/반도체/detail")

        assert response.status_code == 404
        body = response.json()
        assert "반도체" in body["detail"]
        assert "섹터 데이터를 찾을 수 없습니다" in body["detail"]

    def test_get_sector_detail_with_data(self):
        """데이터 있으면 200과 트렌드 + 종목 목록을 반환한다."""
        trend_rows = [
            _make_sector_trend_row("반도체", date(2026, 6, 1), 0.80),
        ]

        # StockMention join 결과 mock (row.krx_code, row.mention_count)
        stock_row = MagicMock()
        stock_row.krx_code = "005930"
        stock_row.mention_count = 3

        session = AsyncMock()
        call_count = 0

        async def side_execute(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # 첫 번째 execute: SectorTrend 쿼리
                mock_sc = MagicMock()
                mock_sc.all.return_value = trend_rows
                mock_res = MagicMock()
                mock_res.scalars.return_value = mock_sc
                return mock_res
            else:
                # 두 번째 execute: StockMention join 쿼리
                mock_res = MagicMock()
                mock_res.all.return_value = [stock_row]
                return mock_res

        session.execute = side_execute

        from stock_picker.api.main import create_app
        from stock_picker.db.session import get_session

        async def override_get_session():
            yield session

        app = create_app()
        app.dependency_overrides[get_session] = override_get_session
        client = TestClient(app)

        response = client.get("/sectors/반도체/detail")

        assert response.status_code == 200
        body = response.json()
        assert body["sector"] == "반도체"
        assert len(body["trends"]) == 1
        assert "stocks" in body
        assert "total_stocks" in body

    def test_get_sector_detail_days_param(self):
        """days 파라미터가 응답에 반영된다."""
        trend_rows = [_make_sector_trend_row("IT")]
        session = AsyncMock()
        call_count = 0

        async def side_execute(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                mock_sc = MagicMock()
                mock_sc.all.return_value = trend_rows
                mock_res = MagicMock()
                mock_res.scalars.return_value = mock_sc
                return mock_res
            mock_res = MagicMock()
            mock_res.all.return_value = []
            return mock_res

        session.execute = side_execute

        from stock_picker.api.main import create_app
        from stock_picker.db.session import get_session

        async def override_get_session():
            yield session

        app = create_app()
        app.dependency_overrides[get_session] = override_get_session
        client = TestClient(app)

        response = client.get("/sectors/IT/detail?days=14")

        assert response.status_code == 200
        assert response.json()["days"] == 14

    def test_get_sector_detail_response_schema(self):
        """상세 응답 스키마 필수 필드 검증."""
        trend_rows = [_make_sector_trend_row("반도체")]
        session = AsyncMock()
        call_count = 0

        async def side_execute(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                mock_sc = MagicMock()
                mock_sc.all.return_value = trend_rows
                mock_res = MagicMock()
                mock_res.scalars.return_value = mock_sc
                return mock_res
            mock_res = MagicMock()
            mock_res.all.return_value = []
            return mock_res

        session.execute = side_execute

        from stock_picker.api.main import create_app
        from stock_picker.db.session import get_session

        async def override_get_session():
            yield session

        app = create_app()
        app.dependency_overrides[get_session] = override_get_session
        client = TestClient(app)

        response = client.get("/sectors/반도체/detail")
        body = response.json()

        required = {"sector", "days", "trends", "stocks", "total_stocks"}
        assert required.issubset(body.keys())


class TestSectorPipelineIntegration:
    """섹터 집계 파이프라인 통합 시나리오 테스트"""

    def test_sector_ranking_default_params(self):
        """기본 파라미터(sort=score, limit=10, days=1)로 랭킹 조회."""
        rows = [_make_sector_trend_row("반도체")]
        session = _make_session_with_sector_trends(rows)
        client = _make_client_with_db(session)

        response = client.get("/sectors/ranking")

        assert response.status_code == 200
        body = response.json()
        assert body["sort"] == "score"
        assert body["limit"] == 10

    def test_sector_ranking_limit_max_50(self):
        """limit 최대값 50 초과 시 422 반환."""
        session = _make_session_with_sector_trends([])
        client = _make_client_with_db(session)

        response = client.get("/sectors/ranking?limit=100")

        assert response.status_code == 422

    def test_sector_trends_and_ranking_coexist(self):
        """기존 /sectors/trends와 새 /sectors/ranking이 함께 정상 응답한다."""
        rows = [_make_sector_trend_row("반도체")]
        session = _make_session_with_sector_trends(rows)
        client = _make_client_with_db(session)

        r1 = client.get("/sectors/trends")
        r2 = client.get("/sectors/ranking")

        assert r1.status_code == 200
        assert r2.status_code == 200
