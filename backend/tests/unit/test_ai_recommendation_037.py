# AI 종목 추천 고도화 단위 테스트 (SPEC-STOCK-037)
# TDD RED-GREEN-REFACTOR 사이클
# asyncio_mode = "auto" — @pytest.mark.asyncio 불필요
from unittest.mock import MagicMock, patch

import pytest


# ──────────────────────────────────────────────────────────────
# TestApplyPreferenceFilter — 선호 필터 순수 함수 (6개 테스트)
# ──────────────────────────────────────────────────────────────


class TestApplyPreferenceFilter:
    """선호 필터 순수 함수 테스트 (REQ-AIEX-APPLY)"""

    def test_disliked_stocks_move_to_end(self):
        """싫어요 종목은 리스트 뒤로 밀려야 한다"""
        from stock_picker.portfolio.ai_recommendation import apply_preference_filter

        recommendations = [
            {"krx_code": "005930", "sector": "반도체", "fit_score": 0.9},
            {"krx_code": "035420", "sector": "IT서비스", "fit_score": 0.8},
            {"krx_code": "000660", "sector": "반도체", "fit_score": 0.7},
        ]
        preferences = [
            {"krx_code": "005930", "sector": "반도체", "preference": "disliked"},
        ]
        result = apply_preference_filter(recommendations, preferences)

        # 싫어요 종목은 마지막이어야 함
        assert result[-1]["krx_code"] == "005930"
        # 나머지는 앞에 유지
        non_disliked = [r for r in result if r["krx_code"] != "005930"]
        assert len(non_disliked) == 2

    def test_liked_same_sector_moves_to_front(self):
        """좋아요 종목과 같은 섹터 종목은 앞으로 이동해야 한다"""
        from stock_picker.portfolio.ai_recommendation import apply_preference_filter

        recommendations = [
            {"krx_code": "000660", "sector": "반도체", "fit_score": 0.6},
            {"krx_code": "035420", "sector": "IT서비스", "fit_score": 0.8},
            {"krx_code": "005930", "sector": "반도체", "fit_score": 0.9},
        ]
        preferences = [
            {"krx_code": "012345", "sector": "반도체", "preference": "liked"},
        ]
        result = apply_preference_filter(recommendations, preferences)

        # 반도체 섹터 종목들이 앞쪽에 있어야 함
        semiconductor_positions = [
            i for i, r in enumerate(result) if r["sector"] == "반도체"
        ]
        it_positions = [
            i for i, r in enumerate(result) if r["sector"] == "IT서비스"
        ]
        # 반도체 섹터 종목들이 IT서비스보다 앞에 있어야 함
        assert min(semiconductor_positions) < min(it_positions)

    def test_empty_preferences_returns_same_order(self):
        """선호가 없으면 동일한 순서를 반환해야 한다"""
        from stock_picker.portfolio.ai_recommendation import apply_preference_filter

        recommendations = [
            {"krx_code": "005930", "sector": "반도체", "fit_score": 0.9},
            {"krx_code": "035420", "sector": "IT서비스", "fit_score": 0.8},
        ]
        result = apply_preference_filter(recommendations, [])

        assert [r["krx_code"] for r in result] == ["005930", "035420"]

    def test_disliked_and_liked_combined(self):
        """싫어요 + 좋아요 동시 적용 시 둘 다 올바르게 처리되어야 한다"""
        from stock_picker.portfolio.ai_recommendation import apply_preference_filter

        recommendations = [
            {"krx_code": "A", "sector": "에너지", "fit_score": 0.5},
            {"krx_code": "B", "sector": "반도체", "fit_score": 0.7},
            {"krx_code": "C", "sector": "반도체", "fit_score": 0.6},
            {"krx_code": "D", "sector": "금융", "fit_score": 0.8},
        ]
        preferences = [
            {"krx_code": "A", "sector": "에너지", "preference": "disliked"},
            {"krx_code": "X", "sector": "반도체", "preference": "liked"},
        ]
        result = apply_preference_filter(recommendations, preferences)

        # 싫어요(A)는 뒤에, 반도체(B,C)는 앞에
        codes = [r["krx_code"] for r in result]
        assert codes[-1] == "A"
        assert codes[0] in ("B", "C")

    def test_unknown_preference_value_treated_as_noop(self):
        """알 수 없는 선호 값은 무시되어야 한다"""
        from stock_picker.portfolio.ai_recommendation import apply_preference_filter

        recommendations = [
            {"krx_code": "005930", "sector": "반도체", "fit_score": 0.9},
            {"krx_code": "035420", "sector": "IT서비스", "fit_score": 0.8},
        ]
        preferences = [
            {"krx_code": "005930", "sector": "반도체", "preference": "unknown_value"},
        ]
        result = apply_preference_filter(recommendations, preferences)

        # 순서 변경 없이 원본 유지
        assert [r["krx_code"] for r in result] == ["005930", "035420"]

    def test_all_disliked_moves_to_end_not_removed(self):
        """전체 싫어요여도 제거하지 않고 후순위로 이동해야 한다"""
        from stock_picker.portfolio.ai_recommendation import apply_preference_filter

        recommendations = [
            {"krx_code": "A", "sector": "에너지", "fit_score": 0.9},
            {"krx_code": "B", "sector": "금융", "fit_score": 0.8},
        ]
        preferences = [
            {"krx_code": "A", "sector": "에너지", "preference": "disliked"},
            {"krx_code": "B", "sector": "금융", "preference": "disliked"},
        ]
        result = apply_preference_filter(recommendations, preferences)

        # 둘 다 존재해야 함 (제거 안 됨)
        assert len(result) == 2
        assert {r["krx_code"] for r in result} == {"A", "B"}


# ──────────────────────────────────────────────────────────────
# TestRankByPortfolioContext — 포트폴리오 맥락 재순위 (5개 테스트)
# ──────────────────────────────────────────────────────────────


class TestRankByPortfolioContext:
    """포트폴리오 맥락 기반 재순위 순수 함수 테스트 (REQ-AIEX-PORT)"""

    def test_owned_holdings_are_excluded(self):
        """보유 중인 종목은 추천에서 제외되어야 한다"""
        from stock_picker.portfolio.ai_recommendation import rank_by_portfolio_context

        recommendations = [
            {"krx_code": "005930", "sector": "반도체", "fit_score": 0.9},
            {"krx_code": "035420", "sector": "IT서비스", "fit_score": 0.8},
        ]
        holdings = [
            {"krx_code": "005930", "sector": "반도체", "weight_pct": 30.0},
        ]
        result = rank_by_portfolio_context(recommendations, holdings)

        codes = [r["krx_code"] for r in result]
        assert "005930" not in codes
        assert "035420" in codes

    def test_sector_over_50pct_excludes_same_sector(self):
        """특정 섹터 비중이 50% 초과 시 해당 섹터 추천 종목은 제외된다"""
        from stock_picker.portfolio.ai_recommendation import rank_by_portfolio_context

        recommendations = [
            {"krx_code": "A", "sector": "반도체", "fit_score": 0.9},
            {"krx_code": "B", "sector": "IT서비스", "fit_score": 0.8},
        ]
        holdings = [
            {"krx_code": "005930", "sector": "반도체", "weight_pct": 30.0},
            {"krx_code": "000660", "sector": "반도체", "weight_pct": 25.0},
            # 반도체 합계 55% > 50%
        ]
        result = rank_by_portfolio_context(recommendations, holdings)

        codes = [r["krx_code"] for r in result]
        # 반도체 초과이므로 A(반도체)는 제외, B(IT서비스)는 유지
        assert "A" not in codes
        assert "B" in codes

    def test_empty_holdings_returns_all_recommendations(self):
        """보유 종목이 없으면 모든 추천이 그대로 반환된다"""
        from stock_picker.portfolio.ai_recommendation import rank_by_portfolio_context

        recommendations = [
            {"krx_code": "005930", "sector": "반도체", "fit_score": 0.9},
            {"krx_code": "035420", "sector": "IT서비스", "fit_score": 0.8},
        ]
        result = rank_by_portfolio_context(recommendations, [])

        assert len(result) == 2

    def test_sector_exactly_50pct_is_not_excluded(self):
        """섹터 비중이 정확히 50%이면 제외하지 않는다 (임계치는 > 50%)"""
        from stock_picker.portfolio.ai_recommendation import rank_by_portfolio_context

        recommendations = [
            {"krx_code": "A", "sector": "반도체", "fit_score": 0.9},
        ]
        holdings = [
            {"krx_code": "005930", "sector": "반도체", "weight_pct": 50.0},
            # 정확히 50% — 초과 아님
        ]
        result = rank_by_portfolio_context(recommendations, holdings)

        # 제외되지 않아야 함
        assert len(result) == 1
        assert result[0]["krx_code"] == "A"

    def test_empty_recommendations_returns_empty(self):
        """빈 추천 입력 시 빈 리스트를 반환한다"""
        from stock_picker.portfolio.ai_recommendation import rank_by_portfolio_context

        result = rank_by_portfolio_context([], [{"krx_code": "005930", "sector": "반도체", "weight_pct": 30.0}])
        assert result == []


# ──────────────────────────────────────────────────────────────
# TestBuildPortfolioContextPrompt — 프롬프트 생성 순수 함수 (3개)
# ──────────────────────────────────────────────────────────────


class TestBuildPortfolioContextPrompt:
    """포트폴리오 컨텍스트 Claude 프롬프트 생성 순수 함수 테스트"""

    def test_prompt_contains_ticker_codes(self):
        """프롬프트에 보유 종목 티커 코드가 포함되어야 한다"""
        from stock_picker.portfolio.ai_recommendation import build_portfolio_context_prompt

        holdings = [
            {"krx_code": "005930", "sector": "반도체", "weight_pct": 50.0},
            {"krx_code": "035420", "sector": "IT서비스", "weight_pct": 50.0},
        ]
        prompt = build_portfolio_context_prompt(holdings)

        assert "005930" in prompt
        assert "035420" in prompt

    def test_prompt_contains_sector_distribution(self):
        """프롬프트에 섹터 분포 정보가 포함되어야 한다"""
        from stock_picker.portfolio.ai_recommendation import build_portfolio_context_prompt

        holdings = [
            {"krx_code": "005930", "sector": "반도체", "weight_pct": 60.0},
            {"krx_code": "035420", "sector": "IT서비스", "weight_pct": 40.0},
        ]
        prompt = build_portfolio_context_prompt(holdings)

        # 섹터 이름이 포함되어야 함
        assert "반도체" in prompt
        assert "IT서비스" in prompt

    def test_empty_holdings_prompt_indicates_no_holdings(self):
        """보유 종목이 없는 경우 프롬프트가 그 사실을 나타내야 한다"""
        from stock_picker.portfolio.ai_recommendation import build_portfolio_context_prompt

        prompt = build_portfolio_context_prompt([])

        # 보유 종목 없음을 나타내는 텍스트가 있어야 함
        assert len(prompt) > 0  # 빈 문자열이 아님
        # "없" 또는 "empty" 등의 표현이 포함될 수 있음
        assert "없" in prompt or "0" in prompt or "empty" in prompt.lower()


# ──────────────────────────────────────────────────────────────
# TestRecommendationSchemas — 스키마 검증 (4개)
# ──────────────────────────────────────────────────────────────


class TestRecommendationSchemas:
    """추천 스키마 유효성 검사 테스트"""

    def test_fit_score_must_be_between_0_and_1(self):
        """fit_score는 0.0~1.0 범위여야 한다"""
        from pydantic import ValidationError

        from stock_picker.portfolio.schemas import PersonalizedRecommendation

        # 유효한 값
        valid = PersonalizedRecommendation(
            krx_code="005930",
            name="삼성전자",
            sector="반도체",
            reason="분산 효과",
            risk_factors="섹터 집중 위험",
            fit_score=0.8,
        )
        assert valid.fit_score == 0.8

        # 범위 초과
        with pytest.raises(ValidationError):
            PersonalizedRecommendation(
                krx_code="005930",
                name="삼성전자",
                sector="반도체",
                reason="분산 효과",
                risk_factors="섹터 집중 위험",
                fit_score=1.5,  # 1.0 초과
            )

    def test_preference_must_be_liked_or_disliked(self):
        """preference 값은 'liked' 또는 'disliked'만 허용된다"""
        from pydantic import ValidationError

        from stock_picker.portfolio.schemas import PreferenceSaveRequest

        # 유효한 값
        valid = PreferenceSaveRequest(krx_code="005930", preference="liked")
        assert valid.preference == "liked"

        # 잘못된 값
        with pytest.raises(ValidationError):
            PreferenceSaveRequest(krx_code="005930", preference="neutral")

    def test_disclaimer_present_in_response(self):
        """RecommendationResponse에는 disclaimer 필드가 있어야 한다"""
        from stock_picker.portfolio.schemas import RecommendationResponse, PersonalizedRecommendation

        response = RecommendationResponse(
            recommendations=[
                PersonalizedRecommendation(
                    krx_code="005930",
                    name="삼성전자",
                    sector="반도체",
                    reason="분산 효과",
                    risk_factors="없음",
                    fit_score=0.8,
                )
            ],
            disclaimer="본 분석은 투자 권유가 아닙니다.",
        )
        assert response.disclaimer != ""
        assert len(response.disclaimer) > 0

    def test_personalized_recommendation_has_required_fields(self):
        """PersonalizedRecommendation에 필수 필드가 모두 있어야 한다"""
        from stock_picker.portfolio.schemas import PersonalizedRecommendation

        rec = PersonalizedRecommendation(
            krx_code="005930",
            name="삼성전자",
            sector="반도체",
            reason="포트폴리오 분산 기여",
            risk_factors="반도체 시황 변동",
            fit_score=0.75,
        )
        assert rec.krx_code == "005930"
        assert rec.reason is not None
        assert rec.risk_factors is not None
        assert 0.0 <= rec.fit_score <= 1.0


# ──────────────────────────────────────────────────────────────
# TestOwnership — 소유권 검증 (4개 — 모두 404 반환 확인)
# ──────────────────────────────────────────────────────────────


class TestOwnership:
    """소유권 위반 시 404 반환 테스트 (REQ-AIEX-OWN-001, REQ-AIEX-NFR-003)

    FastAPI dependency override 패턴 사용 — Depends(get_db_session)·Depends(get_current_user)를
    app.dependency_overrides로 교체해 실제 DB 연결 없이 테스트한다.
    """

    def _make_client(self, mock_user, mock_db):
        """dependency_overrides 설정된 TestClient 반환"""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from stock_picker.auth.dependencies import get_current_user, get_db_session
        from stock_picker.portfolio.router import router

        app = FastAPI()
        app.include_router(router)
        # FastAPI Depends override — patch 대신 dependency_overrides 사용
        app.dependency_overrides[get_db_session] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user
        return TestClient(app, raise_server_exceptions=False)

    def test_post_recommendations_other_portfolio_returns_404(self):
        """다른 사용자 포트폴리오에 POST /recommendations → 404"""
        mock_user = MagicMock()
        mock_user.id = 99  # 다른 사용자
        mock_db = MagicMock()

        client = self._make_client(mock_user, mock_db)

        with patch(
            "stock_picker.portfolio.router.service.get_portfolio_with_holdings",
            return_value=None,  # 소유권 없음 → None
        ):
            response = client.post("/portfolios/999/recommendations")
            assert response.status_code == 404

    def test_post_preferences_other_portfolio_returns_404(self):
        """다른 사용자 포트폴리오에 POST /recommendations/preferences → 404"""
        mock_user = MagicMock()
        mock_user.id = 99
        mock_db = MagicMock()

        client = self._make_client(mock_user, mock_db)

        with patch(
            "stock_picker.portfolio.router.service.get_portfolio_with_holdings",
            return_value=None,
        ):
            response = client.post(
                "/portfolios/999/recommendations/preferences",
                json={"krx_code": "005930", "preference": "liked"},
            )
            assert response.status_code == 404

    def test_get_preferences_other_portfolio_returns_404(self):
        """다른 사용자 포트폴리오에 GET /recommendations/preferences → 404"""
        mock_user = MagicMock()
        mock_user.id = 99
        mock_db = MagicMock()

        client = self._make_client(mock_user, mock_db)

        with patch(
            "stock_picker.portfolio.router.service.get_portfolio_with_holdings",
            return_value=None,
        ):
            response = client.get("/portfolios/999/recommendations/preferences")
            assert response.status_code == 404

    def test_get_history_other_portfolio_returns_404(self):
        """다른 사용자 포트폴리오에 GET /recommendations/history → 404"""
        mock_user = MagicMock()
        mock_user.id = 99
        mock_db = MagicMock()

        client = self._make_client(mock_user, mock_db)

        with patch(
            "stock_picker.portfolio.router.service.get_portfolio_with_holdings",
            return_value=None,
        ):
            response = client.get("/portfolios/999/recommendations/history")
            assert response.status_code == 404


# ──────────────────────────────────────────────────────────────
# TestPreferenceSelectThenWrite — SELECT-then-write 패턴 (2개)
# ──────────────────────────────────────────────────────────────


class TestPreferenceSelectThenWrite:
    """선호 저장 SELECT-then-write 패턴 테스트 (REQ-AIEX-NFR-005)"""

    def test_save_preference_inserts_when_none_exists(self):
        """기존 선호 없으면 INSERT 수행 (ON CONFLICT 사용 안 함)"""
        from stock_picker.portfolio.ai_recommendation import save_preference_select_then_write

        mock_db = MagicMock()
        # SELECT 결과: 없음
        mock_db.query.return_value.filter.return_value.first.return_value = None

        save_preference_select_then_write(
            db=mock_db,
            user_id=1,
            portfolio_id=1,
            krx_code="005930",
            preference="liked",
        )

        # add 호출되어야 함 (INSERT)
        assert mock_db.add.called
        assert mock_db.commit.called

    def test_save_preference_updates_when_exists(self):
        """기존 선호 있으면 UPDATE 수행 (중복 생성 안 함)"""
        from stock_picker.portfolio.ai_recommendation import save_preference_select_then_write
        from stock_picker.db.models import UserRecommendationPreference

        mock_db = MagicMock()

        # 기존 레코드 존재
        existing = MagicMock(spec=UserRecommendationPreference)
        existing.preference = "disliked"
        mock_db.query.return_value.filter.return_value.first.return_value = existing

        save_preference_select_then_write(
            db=mock_db,
            user_id=1,
            portfolio_id=1,
            krx_code="005930",
            preference="liked",
        )

        # add 호출 안 됨 (새 객체 생성 안 함), 기존 레코드 갱신
        assert not mock_db.add.called
        assert existing.preference == "liked"
        assert mock_db.commit.called
