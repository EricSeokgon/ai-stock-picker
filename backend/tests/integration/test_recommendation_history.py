# 추천 히스토리 엔드포인트 통합 테스트 (TASK-011)
# GET /recommendations/history — 날짜별 그룹 반환, 공개 엔드포인트
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient


def _make_rec_orm(
    krx_code: str = "005930",
    rank: int = 1,
    days_ago: int = 0,
    explanation: str | None = None,
) -> MagicMock:
    """Recommendation ORM 객체 모의 생성"""
    rec = MagicMock()
    rec.krx_code = krx_code
    rec.rank = rank
    rec.total_score = Decimal("0.750")
    rec.sentiment_score = Decimal("0.800")
    rec.volume_score = Decimal("0.600")
    rec.momentum_score = Decimal("0.700")
    rec.anomaly_score = Decimal("0.500")
    rec.reasoning = "분석 결과"
    rec.explanation = explanation
    trade_dt = datetime.now(tz=timezone.utc) - timedelta(days=days_ago)
    rec.trade_date = trade_dt
    return rec


def _make_app_with_session(recs: list) -> tuple:
    """앱과 TestClient를 의존성 오버라이드와 함께 반환"""
    from stock_picker.api.main import create_app
    from stock_picker.db.session import get_session

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = recs

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def override_get_session():
        yield mock_session

    app = create_app()
    app.dependency_overrides[get_session] = override_get_session
    return app, TestClient(app)


class TestRecommendationHistoryEndpoint:
    """GET /recommendations/history 통합 테스트"""

    def test_default_days_7_returns_200(self):
        """기본 파라미터(days=7) 요청 시 200 반환"""
        _, client = _make_app_with_session([])

        response = client.get("/recommendations/history")

        assert response.status_code == 200
        body = response.json()
        assert body["days"] == 7
        assert "groups" in body

    def test_days_30_returns_correct_days_field(self):
        """days=30 요청 시 응답의 days 필드가 30"""
        _, client = _make_app_with_session([])

        response = client.get("/recommendations/history?days=30")

        assert response.status_code == 200
        assert response.json()["days"] == 30

    def test_days_0_returns_422(self):
        """days=0 요청 시 422 검증 오류 (ge=1 조건)"""
        _, client = _make_app_with_session([])

        response = client.get("/recommendations/history?days=0")

        assert response.status_code == 422

    def test_days_91_returns_422(self):
        """days=91 요청 시 422 검증 오류 (le=90 조건)"""
        _, client = _make_app_with_session([])

        response = client.get("/recommendations/history?days=91")

        assert response.status_code == 422

    def test_empty_result_returns_empty_groups(self):
        """DB 결과 없을 때 groups=[] 반환"""
        _, client = _make_app_with_session([])

        response = client.get("/recommendations/history?days=7")

        assert response.status_code == 200
        body = response.json()
        assert body["groups"] == []

    def test_no_auth_required(self):
        """인증 헤더 없이도 200 반환 (공개 엔드포인트)"""
        _, client = _make_app_with_session([])

        # Authorization 헤더 없이 요청
        response = client.get("/recommendations/history")

        assert response.status_code == 200

    def test_history_groups_by_date(self):
        """여러 날짜의 데이터가 날짜별로 그룹화되어 반환"""
        recs = [
            _make_rec_orm(krx_code="005930", rank=1, days_ago=0),
            _make_rec_orm(krx_code="000660", rank=2, days_ago=0),
            _make_rec_orm(krx_code="035420", rank=1, days_ago=1),
        ]
        _, client = _make_app_with_session(recs)

        response = client.get("/recommendations/history?days=7")

        assert response.status_code == 200
        body = response.json()
        groups = body["groups"]
        # 2개 날짜 그룹이 있어야 함
        assert len(groups) == 2
        # 각 그룹에 date, recommendations 필드 존재
        for group in groups:
            assert "date" in group
            assert "recommendations" in group

    def test_groups_sorted_newest_first(self):
        """날짜 그룹이 최신순(내림차순)으로 정렬됨"""
        recs = [
            _make_rec_orm(krx_code="005930", rank=1, days_ago=2),
            _make_rec_orm(krx_code="000660", rank=1, days_ago=0),
            _make_rec_orm(krx_code="035420", rank=1, days_ago=1),
        ]
        _, client = _make_app_with_session(recs)

        response = client.get("/recommendations/history?days=7")

        assert response.status_code == 200
        groups = response.json()["groups"]
        dates = [g["date"] for g in groups]
        # 날짜가 내림차순(최신 → 과거) 정렬되어야 함
        assert dates == sorted(dates, reverse=True)

    def test_explanation_field_included_in_items(self):
        """추천 항목에 explanation 필드 포함"""
        recs = [
            _make_rec_orm(
                krx_code="005930",
                rank=1,
                days_ago=0,
                explanation="감성 분석 점수가 높아 긍정적 흐름을 보입니다.",
            )
        ]
        _, client = _make_app_with_session(recs)

        response = client.get("/recommendations/history?days=7")

        assert response.status_code == 200
        groups = response.json()["groups"]
        assert len(groups) == 1
        items = groups[0]["recommendations"]
        assert len(items) == 1
        assert items[0]["explanation"] == "감성 분석 점수가 높아 긍정적 흐름을 보입니다."
