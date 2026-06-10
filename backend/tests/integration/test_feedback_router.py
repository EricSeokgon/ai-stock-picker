# 추천 피드백 라우터 통합 테스트 (SPEC-STOCK-007 TASK-010)
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from stock_picker.db.models import RecommendationFeedback


def _make_feedback_obj(krx_code: str = "005930", vote: str = "up") -> RecommendationFeedback:
    """테스트용 RecommendationFeedback 인스턴스"""
    fb = RecommendationFeedback()
    fb.id = 1
    fb.krx_code = krx_code
    fb.vote = vote
    fb.user_id = None
    return fb


def _make_app_with_mock_feedback(
    save_raises: Exception | None = None,
    summary: dict | None = None,
):
    """피드백 서비스를 mock으로 대체한 앱 반환"""
    from stock_picker.api.main import create_app
    from stock_picker.db.session import get_session
    from unittest.mock import patch

    app = create_app()
    mock_session = AsyncMock()

    async def override_session():
        yield mock_session

    app.dependency_overrides[get_session] = override_session
    return app, mock_session


class TestSubmitFeedbackEndpoint:
    """POST /recommendations/{krx_code}/feedback 엔드포인트 통합 테스트"""

    def test_valid_up_vote_returns_200(self):
        """유효한 up 투표 → 200 응답"""
        from unittest.mock import patch

        app, _ = _make_app_with_mock_feedback()

        # recommendations 라우터에서 임포트된 심볼을 패치
        with (
            patch(
                "stock_picker.api.routes.recommendations.save_feedback",
                new=AsyncMock(return_value=_make_feedback_obj()),
            ),
            patch(
                "stock_picker.api.routes.recommendations.get_feedback_summary",
                new=AsyncMock(return_value={"krx_code": "005930", "up": 1, "down": 0}),
            ),
        ):
            with TestClient(app) as client:
                resp = client.post(
                    "/recommendations/005930/feedback",
                    json={"vote": "up"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert "krx_code" in data
        assert "up" in data
        assert "down" in data

    def test_valid_down_vote_returns_200(self):
        """유효한 down 투표 → 200 응답"""
        from unittest.mock import patch

        app, _ = _make_app_with_mock_feedback()

        with (
            patch(
                "stock_picker.api.routes.recommendations.save_feedback",
                new=AsyncMock(return_value=_make_feedback_obj(vote="down")),
            ),
            patch(
                "stock_picker.api.routes.recommendations.get_feedback_summary",
                new=AsyncMock(return_value={"krx_code": "005930", "up": 0, "down": 1}),
            ),
        ):
            with TestClient(app) as client:
                resp = client.post(
                    "/recommendations/005930/feedback",
                    json={"vote": "down"},
                )

        assert resp.status_code == 200

    def test_invalid_vote_returns_422(self):
        """유효하지 않은 vote 값 → 422"""
        from unittest.mock import patch

        app, _ = _make_app_with_mock_feedback()

        # save_feedback이 ValueError를 발생시키도록 설정
        async def _raise_value_error(*args, **kwargs):
            raise ValueError("투표 값이 유효하지 않습니다: 'maybe'. 허용값: up, down")

        with patch(
            "stock_picker.api.routes.recommendations.save_feedback",
            new=_raise_value_error,
        ):
            with TestClient(app) as client:
                resp = client.post(
                    "/recommendations/005930/feedback",
                    json={"vote": "maybe"},
                )

        assert resp.status_code == 422

    def test_no_auth_accepted_for_feedback(self):
        """인증 없이도 피드백 투표 가능 (선택적 인증)"""
        from unittest.mock import patch

        app, _ = _make_app_with_mock_feedback()

        with (
            patch(
                "stock_picker.api.routes.recommendations.save_feedback",
                new=AsyncMock(return_value=_make_feedback_obj()),
            ),
            patch(
                "stock_picker.api.routes.recommendations.get_feedback_summary",
                new=AsyncMock(return_value={"krx_code": "005930", "up": 1, "down": 0}),
            ),
        ):
            with TestClient(app) as client:
                # Authorization 헤더 없이 요청
                resp = client.post(
                    "/recommendations/005930/feedback",
                    json={"vote": "up"},
                )

        assert resp.status_code == 200


class TestGetFeedbackEndpoint:
    """GET /recommendations/{krx_code}/feedback 엔드포인트 통합 테스트"""

    def test_returns_200_with_counts(self):
        """피드백 조회 → 200 + 카운트 반환"""
        from unittest.mock import patch

        app, _ = _make_app_with_mock_feedback()

        with patch(
            "stock_picker.api.routes.recommendations.get_feedback_summary",
            new=AsyncMock(return_value={"krx_code": "005930", "up": 5, "down": 3}),
        ):
            with TestClient(app) as client:
                resp = client.get("/recommendations/005930/feedback")

        assert resp.status_code == 200
        data = resp.json()
        assert data["up"] == 5
        assert data["down"] == 3

    def test_returns_zero_counts_when_no_feedback(self):
        """피드백 없으면 up=0, down=0"""
        from unittest.mock import patch

        app, _ = _make_app_with_mock_feedback()

        with patch(
            "stock_picker.api.routes.recommendations.get_feedback_summary",
            new=AsyncMock(return_value={"krx_code": "000660", "up": 0, "down": 0}),
        ):
            with TestClient(app) as client:
                resp = client.get("/recommendations/000660/feedback")

        assert resp.status_code == 200
        data = resp.json()
        assert data["up"] == 0
        assert data["down"] == 0
