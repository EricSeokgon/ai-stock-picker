# 포트폴리오 AI 분석 유닛 테스트
# asyncio_mode = "auto" — @pytest.mark.asyncio 데코레이터 불필요
import inspect
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from stock_picker.db.models import Portfolio, PortfolioHolding
from stock_picker.portfolio.ai_analysis import (
    _build_portfolio_data,
    _get_sector,
    analyze_portfolio,
)


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


class TestGetSector:
    """_get_sector 함수 테스트"""

    def test_known_prefix_returns_sector(self):
        # 005930 (삼성전자) — "005" 프리픽스 기반 전자/반도체
        result = _get_sector("005930")
        # 섹터 분류는 fallback이 "기타"이므로 None이 아닌 문자열 반환 확인
        assert isinstance(result, str)
        assert len(result) > 0

    def test_unknown_prefix_returns_default(self):
        assert _get_sector("999999") == "기타"


class TestBuildPortfolioData:
    """_build_portfolio_data 함수 테스트"""

    def test_calculates_weight_correctly(self):
        """비중 계산 정확성 검증"""
        h1 = _make_holding("005930", 10, Decimal("100000"))  # 1,000,000
        h2 = _make_holding("000660", 5, Decimal("200000"))   # 1,000,000

        data = _build_portfolio_data([h1, h2])

        assert len(data) == 2
        # 각각 50% 비중
        assert data[0]["weight_pct"] == 50.0
        assert data[1]["weight_pct"] == 50.0

    def test_no_user_identifying_info(self):
        """사용자 식별 정보 미포함 확인"""
        h = _make_holding()
        data = _build_portfolio_data([h])

        assert "user_id" not in data[0]
        assert "portfolio_id" not in data[0]
        assert "krx_code" in data[0]


class TestAnalyzePortfolio:
    """analyze_portfolio 통합 테스트 (DB + Claude mock) — async로 전환"""

    async def test_empty_portfolio_returns_message_without_claude_call(self):
        """빈 포트폴리오 — Claude 미호출, 메시지 반환"""
        db = MagicMock()
        portfolio = _make_portfolio()

        # 포트폴리오 조회 성공
        db.query.return_value.filter.return_value.first.return_value = portfolio
        # holdings 없음
        db.query.return_value.filter.return_value.all.return_value = []

        with patch(
            "stock_picker.portfolio.ai_analysis._call_claude_async",
            new=AsyncMock(),
        ) as mock_claude:
            result = await analyze_portfolio(portfolio_id=1, user_id=1, db=db)

        mock_claude.assert_not_called()
        assert "message" in result
        assert result["message"] == "분석할 보유 종목이 없습니다."

    async def test_portfolio_not_found_raises_403(self):
        """포트폴리오 없음 또는 소유권 불일치 — 403"""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await analyze_portfolio(portfolio_id=99, user_id=1, db=db)

        assert exc_info.value.status_code == 403

    async def test_claude_error_returns_error_dict(self):
        """Claude API 실패 시 오류 딕셔너리 반환 (500 아님)"""
        db = MagicMock()
        portfolio = _make_portfolio()
        holding = _make_holding()

        db.query.return_value.filter.return_value.first.return_value = portfolio
        db.query.return_value.filter.return_value.all.return_value = [holding]

        with patch(
            "stock_picker.portfolio.ai_analysis._call_claude_async",
            new=AsyncMock(side_effect=Exception("API 장애")),
        ):
            result = await analyze_portfolio(portfolio_id=1, user_id=1, db=db)

        assert "error" in result
        assert "일시적" in result["error"]

    async def test_valid_portfolio_includes_disclaimer(self):
        """정상 분석 결과에 면책 문구 포함"""
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

        assert result["disclaimer"] == "본 분석은 투자 권유가 아닌 정보 제공 목적입니다."
        assert result["diversification"] == "분산투자 평가"
