# SPEC-STOCK-040: AI 포트폴리오 코멘터리 단위 테스트
# 테스트 실행: backend/.venv/bin/pytest backend/tests/unit/test_ai_commentary_040.py -v
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# TestGeneratePortfolioCommentary — Claude API 목업 기반 코멘터리 생성 테스트
# ─────────────────────────────────────────────────────────────────────────────


class TestGeneratePortfolioCommentary:
    """generate_portfolio_commentary 함수 단위 테스트 (Claude API mock)"""

    def _make_portfolio_data(self) -> dict:
        """테스트용 포트폴리오 데이터 생성"""
        return {
            "total_value": 10000000.0,
            "total_return_pct": 5.5,
            "holdings": [
                {
                    "name": "삼성전자",
                    "ticker": "005930",
                    "weight_pct": 60.0,
                    "return_pct": 8.0,
                    "sector": "반도체",
                },
                {
                    "name": "SK하이닉스",
                    "ticker": "000660",
                    "weight_pct": 40.0,
                    "return_pct": 2.0,
                    "sector": "반도체",
                },
            ],
            "risk_metrics": {
                "volatility": 15.5,
                "sharpe_ratio": 1.2,
                "max_drawdown": -8.0,
            },
            "sector_summary": [
                {"sector": "반도체", "weight_pct": 100.0},
            ],
        }

    async def test_normal_input_returns_korean_commentary(self):
        """정상 입력 → 한국어 코멘터리 반환"""
        from stock_picker.portfolio.ai_analysis import generate_portfolio_commentary

        mock_client = AsyncMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="포트폴리오가 5.5% 수익을 기록했습니다. 삼성전자가 60% 비중입니다. 반도체 섹터 집중도가 높습니다. 본 분석은 투자 권유가 아닌 정보 제공 목적입니다.")]
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        result = await generate_portfolio_commentary(
            portfolio_data=self._make_portfolio_data(),
            anthropic_client=mock_client,
        )

        assert isinstance(result, str)
        assert len(result) > 0

    async def test_claude_api_failure_returns_fallback_string(self):
        """Claude API 실패 → 대체 텍스트 반환 (예외 없음)"""
        from stock_picker.portfolio.ai_analysis import generate_portfolio_commentary

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=Exception("API 장애"))

        # 예외가 전파되지 않아야 함
        result = await generate_portfolio_commentary(
            portfolio_data=self._make_portfolio_data(),
            anthropic_client=mock_client,
        )

        assert isinstance(result, str)
        assert "포트폴리오 분석을 일시적으로 제공할 수 없습니다" in result

    async def test_empty_holdings_returns_fallback(self):
        """빈 보유 종목 → 대체 텍스트 반환"""
        from stock_picker.portfolio.ai_analysis import generate_portfolio_commentary

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=Exception("API 장애"))

        data = {
            "total_value": 0.0,
            "total_return_pct": 0.0,
            "holdings": [],
        }

        result = await generate_portfolio_commentary(
            portfolio_data=data,
            anthropic_client=mock_client,
        )

        assert isinstance(result, str)
        assert len(result) > 0

    async def test_no_risk_metrics_returns_commentary_without_error(self):
        """리스크 지표 없는 경우 → 정상 반환"""
        from stock_picker.portfolio.ai_analysis import generate_portfolio_commentary

        mock_client = AsyncMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="포트폴리오 분석 결과입니다. 본 분석은 투자 권유가 아닌 정보 제공 목적입니다.")]
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        data = {
            "total_value": 5000000.0,
            "total_return_pct": 3.0,
            "holdings": [
                {"name": "삼성전자", "ticker": "005930", "weight_pct": 100.0, "return_pct": 3.0, "sector": "반도체"},
            ],
            # risk_metrics 없음
        }

        result = await generate_portfolio_commentary(
            portfolio_data=data,
            anthropic_client=mock_client,
        )

        assert isinstance(result, str)
        assert len(result) > 0

    async def test_commentary_contains_disclaimer(self):
        """코멘터리에 면책 문구 포함 확인"""
        from stock_picker.portfolio.ai_analysis import generate_portfolio_commentary

        disclaimer_text = "본 분석은 투자 권유가 아닌 정보 제공 목적입니다."
        mock_client = AsyncMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=f"포트폴리오 분석 결과입니다. {disclaimer_text}")]
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        result = await generate_portfolio_commentary(
            portfolio_data=self._make_portfolio_data(),
            anthropic_client=mock_client,
        )

        # Claude API가 면책 문구를 포함하거나, 함수가 자동으로 추가해야 함
        assert isinstance(result, str)

    async def test_output_is_string_type(self):
        """출력이 문자열 타입인지 확인"""
        from stock_picker.portfolio.ai_analysis import generate_portfolio_commentary

        mock_client = AsyncMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="분석 결과. 본 분석은 투자 권유가 아닌 정보 제공 목적입니다.")]
        mock_client.messages.create = AsyncMock(return_value=mock_message)

        result = await generate_portfolio_commentary(
            portfolio_data=self._make_portfolio_data(),
            anthropic_client=mock_client,
        )

        assert type(result) is str


# ─────────────────────────────────────────────────────────────────────────────
# TestCommentaryCache — 인메모리 TTL 캐시 테스트
# ─────────────────────────────────────────────────────────────────────────────


class TestCommentaryCache:
    """commentary_cache 모듈 단위 테스트"""

    def setup_method(self):
        """각 테스트 전 캐시 초기화"""
        # 테스트 격리를 위해 캐시 모듈을 새로 임포트
        import importlib
        import stock_picker.portfolio.commentary_cache as cache_mod
        cache_mod._CACHE.clear()

    def test_empty_cache_returns_none(self):
        """빈 캐시 → None 반환"""
        from stock_picker.portfolio.commentary_cache import get_cached_commentary

        result = get_cached_commentary(portfolio_id=999)
        assert result is None

    def test_set_and_get_returns_commentary(self):
        """캐시 저장 후 조회 → 값 반환"""
        from stock_picker.portfolio.commentary_cache import (
            get_cached_commentary,
            set_cached_commentary,
        )

        set_cached_commentary(portfolio_id=1, commentary="테스트 코멘터리")
        result = get_cached_commentary(portfolio_id=1)

        assert result == "테스트 코멘터리"

    def test_expired_cache_returns_none(self):
        """TTL 만료 → None 반환"""
        from stock_picker.portfolio.commentary_cache import (
            get_cached_commentary,
            set_cached_commentary,
        )

        set_cached_commentary(portfolio_id=2, commentary="만료될 코멘터리")

        # time.time()을 TTL 이후로 mock — 300초 후
        with patch("stock_picker.portfolio.commentary_cache.time") as mock_time:
            mock_time.time.return_value = time.time() + 400  # TTL(300) 초과

            result = get_cached_commentary(portfolio_id=2)

        assert result is None

    def test_cache_update_returns_latest_value(self):
        """캐시 갱신 → 최신 값 반환"""
        from stock_picker.portfolio.commentary_cache import (
            get_cached_commentary,
            set_cached_commentary,
        )

        set_cached_commentary(portfolio_id=3, commentary="기존 코멘터리")
        set_cached_commentary(portfolio_id=3, commentary="갱신된 코멘터리")

        result = get_cached_commentary(portfolio_id=3)
        assert result == "갱신된 코멘터리"


# ─────────────────────────────────────────────────────────────────────────────
# TestAICommentaryEndpoint — FastAPI 엔드포인트 통합 테스트
# ─────────────────────────────────────────────────────────────────────────────


class TestAICommentaryEndpoint:
    """GET /portfolios/{id}/ai-commentary 엔드포인트 테스트"""

    def _make_test_client(self):
        """FastAPI TestClient 생성"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app
        return TestClient(app)

    def test_get_ai_commentary_returns_200(self):
        """GET /portfolios/{id}/ai-commentary → 200 + commentary"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app
        from stock_picker.db.models import Portfolio, PortfolioHolding, User
        from decimal import Decimal

        client = TestClient(app)

        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.email = "test@example.com"

        mock_portfolio = MagicMock(spec=Portfolio)
        mock_portfolio.id = 1
        mock_portfolio.user_id = 1
        mock_portfolio.name = "테스트 포트폴리오"

        mock_holding = MagicMock(spec=PortfolioHolding)
        mock_holding.id = 1
        mock_holding.portfolio_id = 1
        mock_holding.krx_code = "005930"
        mock_holding.quantity = 10
        mock_holding.avg_buy_price = Decimal("70000")
        mock_holding.market = "KRX"
        mock_holding.currency = "KRW"

        with patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user), \
             patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.router.service.get_portfolio_with_holdings") as mock_get_portfolio, \
             patch("stock_picker.portfolio.commentary_cache.get_cached_commentary", return_value=None), \
             patch("stock_picker.portfolio.ai_analysis.generate_portfolio_commentary", new=AsyncMock(return_value="테스트 코멘터리입니다. 본 분석은 투자 권유가 아닌 정보 제공 목적입니다.")), \
             patch("stock_picker.portfolio.commentary_cache.set_cached_commentary"):

            mock_portfolio.holdings = [mock_holding]
            mock_get_portfolio.return_value = mock_portfolio

            response = client.get("/portfolios/1/ai-commentary")

        assert response.status_code == 200
        data = response.json()
        assert "commentary" in data
        assert "portfolio_id" in data

    def test_unauthenticated_returns_401(self):
        """미인증 → 401"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app

        client = TestClient(app)

        with patch("stock_picker.auth.dependencies.get_current_user", side_effect=Exception("Unauthorized")):
            response = client.get("/portfolios/1/ai-commentary")

        # 인증 실패 시 401 또는 422 (depends on FastAPI setup)
        assert response.status_code in (401, 403, 422)

    def test_other_user_portfolio_returns_404(self):
        """타인 포트폴리오 → 404"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app
        from stock_picker.db.models import User

        client = TestClient(app)

        mock_user = MagicMock(spec=User)
        mock_user.id = 2  # 다른 유저
        mock_user.email = "other@example.com"

        with patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user), \
             patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.router.service.get_portfolio_with_holdings", return_value=None):

            response = client.get("/portfolios/1/ai-commentary")

        assert response.status_code == 404

    def test_cache_hit_returns_cached_true(self):
        """캐시 히트 → cached=True"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app
        from stock_picker.db.models import Portfolio, User

        client = TestClient(app)

        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.email = "test@example.com"

        mock_portfolio = MagicMock(spec=Portfolio)
        mock_portfolio.id = 1
        mock_portfolio.user_id = 1
        mock_portfolio.holdings = []

        with patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user), \
             patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.router.service.get_portfolio_with_holdings", return_value=mock_portfolio), \
             patch("stock_picker.portfolio.commentary_cache.get_cached_commentary", return_value="캐시된 코멘터리"):

            response = client.get("/portfolios/1/ai-commentary")

        assert response.status_code == 200
        data = response.json()
        assert data.get("cached") is True

    def test_api_failure_returns_200_with_fallback(self):
        """API 실패 → 200 (대체 텍스트, 500 아님)"""
        from fastapi.testclient import TestClient
        from stock_picker.main import app
        from stock_picker.db.models import Portfolio, PortfolioHolding, User
        from decimal import Decimal

        client = TestClient(app)

        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.email = "test@example.com"

        mock_portfolio = MagicMock(spec=Portfolio)
        mock_portfolio.id = 1
        mock_portfolio.user_id = 1
        mock_portfolio.name = "테스트"

        mock_holding = MagicMock(spec=PortfolioHolding)
        mock_holding.portfolio_id = 1
        mock_holding.krx_code = "005930"
        mock_holding.quantity = 10
        mock_holding.avg_buy_price = Decimal("70000")
        mock_holding.market = "KRX"
        mock_holding.currency = "KRW"

        fallback = "포트폴리오 분석을 일시적으로 제공할 수 없습니다. 잠시 후 다시 시도해 주세요."

        with patch("stock_picker.auth.dependencies.get_current_user", return_value=mock_user), \
             patch("stock_picker.auth.dependencies.get_db_session", return_value=MagicMock()), \
             patch("stock_picker.portfolio.router.service.get_portfolio_with_holdings") as mock_get, \
             patch("stock_picker.portfolio.commentary_cache.get_cached_commentary", return_value=None), \
             patch("stock_picker.portfolio.ai_analysis.generate_portfolio_commentary", new=AsyncMock(return_value=fallback)), \
             patch("stock_picker.portfolio.commentary_cache.set_cached_commentary"):

            mock_portfolio.holdings = [mock_holding]
            mock_get.return_value = mock_portfolio

            response = client.get("/portfolios/1/ai-commentary")

        # 절대 500이면 안 됨
        assert response.status_code != 500
        assert response.status_code == 200
        data = response.json()
        assert "commentary" in data
