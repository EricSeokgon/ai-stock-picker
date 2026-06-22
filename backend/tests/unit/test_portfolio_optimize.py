# 포트폴리오 AI 최적화 분석 유닛 테스트 (SPEC-STOCK-026)
# asyncio_mode = "auto" — @pytest.mark.asyncio 데코레이터 불필요
import inspect
import json
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from stock_picker.db.models import Portfolio, PortfolioHolding
from stock_picker.portfolio.schemas import OptimizeResult


def _make_portfolio(id: int = 1, user_id: int = 1) -> Portfolio:
    p = Portfolio()
    p.id = id
    p.user_id = user_id
    p.name = "테스트 포트폴리오"
    return p


def _make_holding(
    krx_code: str = "005930",
    quantity: int = 10,
    avg_buy_price: Decimal = Decimal("70000.00"),
) -> PortfolioHolding:
    h = PortfolioHolding()
    h.id = 1
    h.portfolio_id = 1
    h.krx_code = krx_code
    h.quantity = quantity
    h.avg_buy_price = avg_buy_price
    return h


# Claude가 반환할 최적화 결과 mock 데이터
def _mock_optimize_response(
    diversification: int = 70,
    risk_balance: int = 60,
    momentum: int = 80,
    target_weights: list | None = None,
    new_stocks: list | None = None,
) -> dict:
    """Claude API 응답을 흉내 내는 딕셔너리 생성"""
    if target_weights is None:
        target_weights = [
            {"krx_code": "005930", "current_pct": 50.0, "target_pct": 40.0},
            {"krx_code": "000660", "current_pct": 30.0, "target_pct": 35.0},
            {"krx_code": "051910", "current_pct": 20.0, "target_pct": 25.0},
        ]
    if new_stocks is None:
        new_stocks = [
            {"krx_code": "035420", "name": "NAVER", "sector": "IT", "reason": "성장 잠재력"},
        ]
    return {
        "score_breakdown": {
            "diversification": diversification,
            "risk_balance": risk_balance,
            "momentum": momentum,
        },
        "target_weights": target_weights,
        "new_stocks": new_stocks,
        "summary": "포트폴리오 분석 결과입니다. 본 분석은 투자 권유가 아닙니다.",
    }


class TestOptimizeScoreRange:
    """score는 0~100 범위 내에 있어야 한다"""

    async def test_optimize_score_range(self):
        """ScoreBreakdown 평균으로 계산된 score가 0~100 범위인지 검증"""
        from stock_picker.portfolio import service

        db = MagicMock()
        redis = AsyncMock()
        portfolio = _make_portfolio()
        holding = _make_holding("005930", 10, Decimal("70000"))

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [holding]

        # Redis 캐시 미스
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        # today 쿼리도 mock (recommendations 없음)
        mock_rec_query = MagicMock()
        mock_rec_query.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        # Claude 응답 mock (diversification=70, risk_balance=60, momentum=80 → score=70)
        claude_response = _mock_optimize_response(70, 60, 80)

        with patch(
            "stock_picker.portfolio.ai_analysis.optimize_portfolio_with_claude",
            new=AsyncMock(return_value=claude_response),
        ):
            result = await service.optimize_portfolio(
                portfolio_id=1, user_id=1, db=db, redis=redis
            )

        assert isinstance(result, OptimizeResult)
        assert 0 <= result.score <= 100


class TestOptimizeTargetWeightsSum100:
    """target_weights의 target_pct 합계는 100.0이어야 한다"""

    async def test_optimize_target_weights_sum_100(self):
        """리밸런싱 비중의 합계가 100%인지 검증"""
        from stock_picker.portfolio import service

        db = MagicMock()
        redis = AsyncMock()
        portfolio = _make_portfolio()
        holdings = [
            _make_holding("005930", 10, Decimal("70000")),
            _make_holding("000660", 5, Decimal("100000")),
            _make_holding("051910", 3, Decimal("150000")),
        ]
        holdings[1].krx_code = "000660"
        holdings[2].krx_code = "051910"

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = holdings

        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        # 합계가 정확히 100인 target_weights
        target_weights = [
            {"krx_code": "005930", "current_pct": 50.0, "target_pct": 40.0},
            {"krx_code": "000660", "current_pct": 30.0, "target_pct": 35.0},
            {"krx_code": "051910", "current_pct": 20.0, "target_pct": 25.0},
        ]
        claude_response = _mock_optimize_response(target_weights=target_weights)

        with patch(
            "stock_picker.portfolio.ai_analysis.optimize_portfolio_with_claude",
            new=AsyncMock(return_value=claude_response),
        ):
            result = await service.optimize_portfolio(
                portfolio_id=1, user_id=1, db=db, redis=redis
            )

        total = sum(item.target_pct for item in result.target_weights)
        assert abs(total - 100.0) < 0.01, f"target_pct 합계가 100이 아님: {total}"


class TestOptimizeActionDirection:
    """2% 임계값 규칙에 따라 action이 올바르게 결정되어야 한다"""

    async def test_optimize_action_direction(self):
        """A=50%→40%(sell), B=30%→35%(buy), C=20%→25%(buy) — 2% 임계값 검증"""
        from stock_picker.portfolio import service

        db = MagicMock()
        redis = AsyncMock()
        portfolio = _make_portfolio()

        # 세 종목 holdings
        h1 = _make_holding("005930", 10, Decimal("100000"))  # 1,000,000
        h2 = _make_holding("000660", 3, Decimal("100000"))   # 300,000
        h2.krx_code = "000660"
        h3 = _make_holding("051910", 2, Decimal("100000"))   # 200,000
        h3.krx_code = "051910"

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [h1, h2, h3]

        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        # Claude가 target_pct를 반환 (action은 서버에서 재계산)
        target_weights = [
            {"krx_code": "005930", "current_pct": 50.0, "target_pct": 40.0},  # -10% → sell
            {"krx_code": "000660", "current_pct": 30.0, "target_pct": 35.0},  # +5% → buy
            {"krx_code": "051910", "current_pct": 20.0, "target_pct": 25.0},  # +5% → buy
        ]
        claude_response = _mock_optimize_response(target_weights=target_weights)

        with patch(
            "stock_picker.portfolio.ai_analysis.optimize_portfolio_with_claude",
            new=AsyncMock(return_value=claude_response),
        ):
            result = await service.optimize_portfolio(
                portfolio_id=1, user_id=1, db=db, redis=redis
            )

        # action 검증
        actions = {item.krx_code: item.action for item in result.target_weights}
        assert actions["005930"] == "sell", f"005930 action={actions['005930']}, expected sell"
        assert actions["000660"] == "buy", f"000660 action={actions['000660']}, expected buy"
        assert actions["051910"] == "buy", f"051910 action={actions['051910']}, expected buy"


class TestOptimizeNewStocksNotInPortfolio:
    """new_stocks는 포트폴리오에 없는 종목만 포함해야 한다"""

    async def test_optimize_new_stocks_not_in_portfolio(self):
        """포트폴리오 보유 종목은 new_stocks에서 제외 검증"""
        from stock_picker.portfolio import service
        from stock_picker.db.models import Recommendation

        db = MagicMock()
        redis = AsyncMock()
        portfolio = _make_portfolio()

        # 포트폴리오에 005930, 000660 보유
        h1 = _make_holding("005930", 10, Decimal("70000"))
        h2 = _make_holding("000660", 5, Decimal("100000"))
        h2.krx_code = "000660"
        holdings = [h1, h2]

        # 첫 번째 쿼리: portfolio, 두 번째 쿼리: holdings
        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = holdings

        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        # Claude 응답에 005930(포트폴리오), 035420, 051910(비보유) 포함
        new_stocks = [
            {"krx_code": "005930", "name": "삼성전자", "sector": "전자", "reason": "테스트"},
            {"krx_code": "035420", "name": "NAVER", "sector": "IT", "reason": "성장"},
            {"krx_code": "051910", "name": "LG화학", "sector": "화학", "reason": "배당"},
        ]
        target_weights = [
            {"krx_code": "005930", "current_pct": 70.0, "target_pct": 65.0},
            {"krx_code": "000660", "current_pct": 30.0, "target_pct": 35.0},
        ]
        claude_response = _mock_optimize_response(
            target_weights=target_weights, new_stocks=new_stocks
        )

        with patch(
            "stock_picker.portfolio.ai_analysis.optimize_portfolio_with_claude",
            new=AsyncMock(return_value=claude_response),
        ):
            result = await service.optimize_portfolio(
                portfolio_id=1, user_id=1, db=db, redis=redis
            )

        # 005930은 포트폴리오에 있으므로 new_stocks에 포함되면 안 됨
        new_codes = [s.krx_code for s in result.new_stocks]
        assert "005930" not in new_codes, "포트폴리오 보유 종목이 new_stocks에 포함됨"
        # 035420, 051910은 포함되어야 함
        assert "035420" in new_codes
        assert "051910" in new_codes


class TestOptimizeRedisCacheHit:
    """두 번째 호출 시 Redis 캐시에서 반환되어야 한다"""

    async def test_optimize_redis_cache_hit(self):
        """캐시 히트 시 Claude를 호출하지 않아야 한다"""
        from stock_picker.portfolio import service

        db = MagicMock()
        redis = AsyncMock()
        portfolio = _make_portfolio()
        holding = _make_holding()

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [holding]

        # 첫 번째 호출: 캐시 미스
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        claude_response = _mock_optimize_response()

        with patch(
            "stock_picker.portfolio.ai_analysis.optimize_portfolio_with_claude",
            new=AsyncMock(return_value=claude_response),
        ) as mock_claude:
            result1 = await service.optimize_portfolio(
                portfolio_id=1, user_id=1, db=db, redis=redis
            )
            assert mock_claude.called, "첫 번째 호출 시 Claude가 호출되어야 함"
            call_count_after_first = mock_claude.call_count

            # 두 번째 호출: 캐시 히트 (JSON 직렬화된 결과 반환)
            redis.get = AsyncMock(return_value=result1.model_dump_json())
            mock_claude.reset_mock()

            result2 = await service.optimize_portfolio(
                portfolio_id=1, user_id=1, db=db, redis=redis
            )

        # 캐시 히트 시 Claude 미호출
        assert not mock_claude.called, "캐시 히트 시 Claude가 호출되면 안 됨"
        assert isinstance(result2, OptimizeResult)


class TestOptimizeAsyncClient:
    """AsyncAnthropic 클라이언트를 사용해야 한다"""

    async def test_optimize_async_client(self):
        """optimize_portfolio_with_claude가 AsyncAnthropic을 사용하는지 검증"""
        import anthropic
        from stock_picker.portfolio.ai_analysis import optimize_portfolio_with_claude

        # 함수 자체가 async인지 확인
        assert inspect.iscoroutinefunction(
            optimize_portfolio_with_claude
        ), "optimize_portfolio_with_claude는 async def여야 함"

        # AsyncAnthropic mock으로 호출 검증
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = json.dumps(_mock_optimize_response())

        with patch("anthropic.AsyncAnthropic") as MockAsyncAnthropic:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            MockAsyncAnthropic.return_value = mock_client

            holdings_data = [
                {"krx_code": "005930", "weight_pct": 100.0, "quantity": 10, "sector": "전자"}
            ]
            db = MagicMock()
            # recommendations 쿼리 — 빈 결과
            db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

            await optimize_portfolio_with_claude(holdings_data, [], db)

        # AsyncAnthropic이 호출되었는지 확인
        MockAsyncAnthropic.assert_called_once()

    async def test_analyze_portfolio_is_async(self):
        """analyze_portfolio가 async def인지 검증 (sync → async 전환 확인)"""
        from stock_picker.portfolio.ai_analysis import analyze_portfolio

        assert inspect.iscoroutinefunction(
            analyze_portfolio
        ), "analyze_portfolio는 async def여야 함"


class TestExistingAiAnalysisAsync:
    """기존 AI 분석 기능이 async로 전환되었는지 검증"""

    async def test_existing_ai_analysis_async(self):
        """analyze_portfolio가 비동기로 호출 가능하고 disclaimer를 반환하는지 검증"""
        from stock_picker.portfolio.ai_analysis import analyze_portfolio

        # async def인지 확인
        assert inspect.iscoroutinefunction(analyze_portfolio)

        db = MagicMock()
        portfolio = _make_portfolio()
        holding = _make_holding()

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [holding]

        mock_analysis = {
            "diversification": "분산투자 평가",
            "risk": "중간 위험",
            "suggestions": "분산 필요",
        }

        with patch(
            "stock_picker.portfolio.ai_analysis._call_claude_async",
            new=AsyncMock(return_value=mock_analysis),
        ):
            result = await analyze_portfolio(portfolio_id=1, user_id=1, db=db)

        assert "disclaimer" in result
        assert result["disclaimer"] == "본 분석은 투자 권유가 아닌 정보 제공 목적입니다."


# ──────────────────────────────────────────────────────────────
# T-008: optimize_portfolio 해외 자산 지원 (SPEC-STOCK-028)
# ──────────────────────────────────────────────────────────────

def _make_holding_foreign(
    krx_code: str = "AAPL",
    quantity: int = 5,
    avg_buy_price: Decimal = Decimal("150.00"),
    market: str = "NASDAQ",
    currency: str = "USD",
) -> PortfolioHolding:
    h = PortfolioHolding()
    h.id = 2
    h.portfolio_id = 1
    h.krx_code = krx_code
    h.quantity = quantity
    h.avg_buy_price = avg_buy_price
    h.market = market
    h.currency = currency
    return h


class TestOptimizePortfolioForeignAsset:
    """T-008: optimize_portfolio 해외 자산 지원 테스트"""

    async def test_holdings_data_includes_market_and_currency(self):
        """optimize_portfolio가 Claude에 넘기는 holdings_data에 market/currency 포함"""
        from unittest.mock import AsyncMock, MagicMock, patch
        from stock_picker.portfolio.service import optimize_portfolio

        db = MagicMock()
        redis = AsyncMock()
        portfolio = _make_portfolio()
        h_krx = _make_holding("005930", 10, Decimal("70000.00"))
        h_nasdaq = _make_holding_foreign("AAPL", 5, Decimal("150.00"), "NASDAQ", "USD")

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [h_krx, h_nasdaq]

        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        captured_holdings_data = []

        async def mock_optimize(holdings_data, portfolio_codes, db_session):
            captured_holdings_data.extend(holdings_data)
            return _mock_optimize_response()

        with patch(
            "stock_picker.portfolio.ai_analysis.optimize_portfolio_with_claude",
            side_effect=mock_optimize,
        ):
            await optimize_portfolio(portfolio_id=1, user_id=1, db=db, redis=redis)

        krx_item = next((d for d in captured_holdings_data if d["krx_code"] == "005930"), None)
        nasdaq_item = next((d for d in captured_holdings_data if d["krx_code"] == "AAPL"), None)

        assert krx_item is not None
        assert "market" in krx_item
        assert "currency" in krx_item

        assert nasdaq_item is not None
        assert "market" in nasdaq_item
        assert nasdaq_item["market"] == "NASDAQ"
        assert nasdaq_item["currency"] == "USD"

    async def test_new_stocks_limited_to_krx(self):
        """new_stocks 추천은 현재 포트폴리오 미보유 종목만 포함 (기존 필터 보존)"""
        from unittest.mock import AsyncMock, MagicMock, patch
        from stock_picker.portfolio.service import optimize_portfolio

        db = MagicMock()
        redis = AsyncMock()
        portfolio = _make_portfolio()
        h = _make_holding("005930", 10, Decimal("70000.00"))
        h2 = _make_holding("000660", 5, Decimal("100000.00"))

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [h, h2]

        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock()

        # new_stocks에 이미 보유 중인 종목 포함 → 제외되어야 함
        response = _mock_optimize_response(
            new_stocks=[
                {"krx_code": "005930", "name": "삼성전자", "sector": "IT", "reason": "이미 보유"},
                {"krx_code": "035420", "name": "NAVER", "sector": "IT", "reason": "추가 검토"},
            ]
        )

        with patch(
            "stock_picker.portfolio.ai_analysis.optimize_portfolio_with_claude",
            new=AsyncMock(return_value=response),
        ):
            result = await optimize_portfolio(portfolio_id=1, user_id=1, db=db, redis=redis)

        new_codes = [ns.krx_code for ns in result.new_stocks]
        assert "005930" not in new_codes
        assert "035420" in new_codes
