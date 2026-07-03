"""포트폴리오 알림 확장 단위 테스트 (SPEC-STOCK-036).

TDD RED 단계: portfolio_value_below, holding_return 2종 신규 알림 타입 검증.
구현 전 먼저 작성하여 실패 확인 후 GREEN으로 구현.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


# ────────────────────────────────────────────────────────────
# 테스트용 헬퍼 객체
# ────────────────────────────────────────────────────────────


def _make_alert_036(
    id: int = 1,
    user_id: int = 1,
    portfolio_id: int = 10,
    alert_type: str = "portfolio_value_below",
    condition_value: float = 1_000_000.0,
    is_active: bool = True,
    is_triggered: bool = False,
    target_krx_code: str | None = None,
    condition_direction: str | None = None,
) -> Any:
    """SPEC-036 확장 필드를 포함한 PortfolioAlert 모의 객체 생성."""
    alert = MagicMock()
    alert.id = id
    alert.user_id = user_id
    alert.portfolio_id = portfolio_id
    alert.alert_type = alert_type
    alert.condition_value = condition_value
    alert.is_active = is_active
    alert.is_triggered = is_triggered
    alert.target_krx_code = target_krx_code
    alert.condition_direction = condition_direction
    return alert


# ────────────────────────────────────────────────────────────
# 1. 순수 함수 테스트: check_portfolio_value_alert
# ────────────────────────────────────────────────────────────


class TestCheckPortfolioValueAlert:
    """포트폴리오 평가액 이하 임계 확인 — portfolio_value_below 타입 (REQ-PAL-036-001)."""

    def test_fires_when_value_below_threshold(self) -> None:
        """평가액이 임계값 미만이면 발화해야 한다."""
        from stock_picker.portfolio.portfolio_alerts import check_portfolio_value_alert

        alert = _make_alert_036(condition_value=1_000_000.0)
        fired, msg = check_portfolio_value_alert(alert, current_value_krw=800_000.0)

        assert fired is True

    def test_no_fire_when_value_above_threshold(self) -> None:
        """평가액이 임계값 초과이면 발화하지 않아야 한다."""
        from stock_picker.portfolio.portfolio_alerts import check_portfolio_value_alert

        alert = _make_alert_036(condition_value=1_000_000.0)
        fired, msg = check_portfolio_value_alert(alert, current_value_krw=1_200_000.0)

        assert fired is False
        assert msg == ""

    def test_fires_on_exact_equal(self) -> None:
        """평가액 == 임계값(경계)이면 발화해야 한다 (≤ 조건)."""
        from stock_picker.portfolio.portfolio_alerts import check_portfolio_value_alert

        alert = _make_alert_036(condition_value=1_000_000.0)
        fired, msg = check_portfolio_value_alert(alert, current_value_krw=1_000_000.0)

        assert fired is True

    def test_returns_message_when_fired(self) -> None:
        """발화 시 현재 평가액과 임계값을 포함한 메시지를 반환해야 한다."""
        from stock_picker.portfolio.portfolio_alerts import check_portfolio_value_alert

        alert = _make_alert_036(condition_value=1_000_000.0)
        fired, msg = check_portfolio_value_alert(alert, current_value_krw=800_000.0)

        assert fired is True
        assert "800,000" in msg
        assert "1,000,000" in msg

    def test_returns_empty_message_when_not_fired(self) -> None:
        """미발화 시 빈 문자열을 반환해야 한다."""
        from stock_picker.portfolio.portfolio_alerts import check_portfolio_value_alert

        alert = _make_alert_036(condition_value=1_000_000.0)
        fired, msg = check_portfolio_value_alert(alert, current_value_krw=1_500_000.0)

        assert fired is False
        assert msg == ""

    def test_zero_threshold_fires_on_zero_value(self) -> None:
        """임계값이 0원이고 평가액도 0원이면 발화해야 한다 (경계 케이스)."""
        from stock_picker.portfolio.portfolio_alerts import check_portfolio_value_alert

        alert = _make_alert_036(condition_value=0.0)
        fired, msg = check_portfolio_value_alert(alert, current_value_krw=0.0)

        assert fired is True

    def test_zero_threshold_no_fire_when_value_positive(self) -> None:
        """임계값이 0원이고 평가액이 양수이면 발화하지 않아야 한다."""
        from stock_picker.portfolio.portfolio_alerts import check_portfolio_value_alert

        alert = _make_alert_036(condition_value=0.0)
        fired, msg = check_portfolio_value_alert(alert, current_value_krw=1.0)

        assert fired is False


# ────────────────────────────────────────────────────────────
# 2. 순수 함수 테스트: check_holding_return_alert
# ────────────────────────────────────────────────────────────


class TestCheckHoldingReturnAlert:
    """개별 종목 수익률 임계 확인 — holding_return 타입 (REQ-PAL-036-002)."""

    def test_fires_when_return_above_threshold_direction_above(self) -> None:
        """above 방향: 수익률 >= 임계값이면 발화해야 한다."""
        from stock_picker.portfolio.portfolio_alerts import check_holding_return_alert

        alert = _make_alert_036(
            alert_type="holding_return",
            condition_value=15.0,
            target_krx_code="005930",
            condition_direction="above",
        )
        fired, msg = check_holding_return_alert(alert, holding_return_pct=20.0)

        assert fired is True

    def test_fires_when_return_below_threshold_direction_below(self) -> None:
        """below 방향: 수익률 <= 임계값이면 발화해야 한다."""
        from stock_picker.portfolio.portfolio_alerts import check_holding_return_alert

        alert = _make_alert_036(
            alert_type="holding_return",
            condition_value=-10.0,
            target_krx_code="005930",
            condition_direction="below",
        )
        fired, msg = check_holding_return_alert(alert, holding_return_pct=-15.0)

        assert fired is True

    def test_no_fire_above_direction_when_below_threshold(self) -> None:
        """above 방향: 수익률 < 임계값이면 발화하지 않아야 한다."""
        from stock_picker.portfolio.portfolio_alerts import check_holding_return_alert

        alert = _make_alert_036(
            alert_type="holding_return",
            condition_value=15.0,
            target_krx_code="005930",
            condition_direction="above",
        )
        fired, msg = check_holding_return_alert(alert, holding_return_pct=10.0)

        assert fired is False
        assert msg == ""

    def test_no_fire_below_direction_when_above_threshold(self) -> None:
        """below 방향: 수익률 > 임계값이면 발화하지 않아야 한다."""
        from stock_picker.portfolio.portfolio_alerts import check_holding_return_alert

        alert = _make_alert_036(
            alert_type="holding_return",
            condition_value=-10.0,
            target_krx_code="005930",
            condition_direction="below",
        )
        fired, msg = check_holding_return_alert(alert, holding_return_pct=-5.0)

        assert fired is False
        assert msg == ""

    def test_default_direction_is_above_when_none(self) -> None:
        """condition_direction=None이면 기본값 'above'로 동작해야 한다."""
        from stock_picker.portfolio.portfolio_alerts import check_holding_return_alert

        alert = _make_alert_036(
            alert_type="holding_return",
            condition_value=10.0,
            target_krx_code="005930",
            condition_direction=None,  # None → above 기본값
        )
        # above 방향: 20.0 >= 10.0 → 발화
        fired, msg = check_holding_return_alert(alert, holding_return_pct=20.0)

        assert fired is True

    def test_returns_message_with_ticker_when_fired(self) -> None:
        """발화 시 종목코드를 포함한 메시지를 반환해야 한다."""
        from stock_picker.portfolio.portfolio_alerts import check_holding_return_alert

        alert = _make_alert_036(
            alert_type="holding_return",
            condition_value=10.0,
            target_krx_code="005930",
            condition_direction="above",
        )
        fired, msg = check_holding_return_alert(alert, holding_return_pct=20.0)

        assert fired is True
        assert "005930" in msg

    def test_exact_equal_below_direction_fires(self) -> None:
        """below 방향 경계: 수익률 == 임계값이면 발화해야 한다 (≤ 조건)."""
        from stock_picker.portfolio.portfolio_alerts import check_holding_return_alert

        alert = _make_alert_036(
            alert_type="holding_return",
            condition_value=-10.0,
            target_krx_code="000660",
            condition_direction="below",
        )
        fired, msg = check_holding_return_alert(alert, holding_return_pct=-10.0)

        assert fired is True

    def test_empty_message_when_not_fired(self) -> None:
        """미발화 시 빈 문자열을 반환해야 한다."""
        from stock_picker.portfolio.portfolio_alerts import check_holding_return_alert

        alert = _make_alert_036(
            alert_type="holding_return",
            condition_value=30.0,
            target_krx_code="005930",
            condition_direction="above",
        )
        fired, msg = check_holding_return_alert(alert, holding_return_pct=10.0)

        assert fired is False
        assert msg == ""


# ────────────────────────────────────────────────────────────
# 3. 스키마 테스트
# ────────────────────────────────────────────────────────────


class TestPortfolioAlertSchemas036:
    """SPEC-036 신규 알림 타입 스키마 검증."""

    def test_alert_create_accepts_portfolio_value_below(self) -> None:
        """PortfolioAlertCreate가 'portfolio_value_below' 타입을 허용해야 한다."""
        from stock_picker.portfolio.schemas import PortfolioAlertCreate

        obj = PortfolioAlertCreate(
            alert_type="portfolio_value_below",
            condition_value=1_000_000.0,
        )
        assert obj.alert_type == "portfolio_value_below"
        assert obj.condition_value == 1_000_000.0

    def test_alert_create_accepts_holding_return_with_krx_code(self) -> None:
        """PortfolioAlertCreate가 'holding_return' 타입과 target_krx_code를 허용해야 한다."""
        from stock_picker.portfolio.schemas import PortfolioAlertCreate

        obj = PortfolioAlertCreate(
            alert_type="holding_return",
            condition_value=15.0,
            target_krx_code="005930",
            condition_direction="above",
        )
        assert obj.alert_type == "holding_return"
        assert obj.target_krx_code == "005930"
        assert obj.condition_direction == "above"

    def test_alert_evaluate_result_fired_true(self) -> None:
        """AlertEvaluateResult: fired=True 케이스 구성 검증."""
        from stock_picker.portfolio.schemas import AlertEvaluateResult

        obj = AlertEvaluateResult(
            alert_id=1,
            alert_type="portfolio_value_below",
            fired=True,
            message="포트폴리오 평가액 800,000원이 임계값 1,000,000원 이하입니다",
        )
        assert obj.fired is True
        assert obj.alert_id == 1

    def test_alert_history_item_schema(self) -> None:
        """AlertHistoryItem 스키마 구성 검증."""
        from stock_picker.portfolio.schemas import AlertHistoryItem

        obj = AlertHistoryItem(
            notification_id=42,
            alert_type="portfolio_value_below",
            message="test message",
            triggered_at=datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc),
            portfolio_id=10,
        )
        assert obj.notification_id == 42
        assert obj.portfolio_id == 10


# ────────────────────────────────────────────────────────────
# 4. API 소유권 검증 테스트
# ────────────────────────────────────────────────────────────


class TestAlertOwnership036:
    """소유권 위반 시 404 반환 검증 (NFR-005, SPEC-036)."""

    @pytest.mark.asyncio
    async def test_evaluate_returns_404_when_portfolio_not_owned(self) -> None:
        """POST /alerts/evaluate: 소유권 불일치 시 404를 반환해야 한다."""
        from stock_picker.portfolio.portfolio_alerts import evaluate_portfolio_alerts

        # execute() 결과에서 scalar_one_or_none()이 None을 동기 반환하도록 모의
        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        session = AsyncMock()
        session.execute.return_value = execute_result

        result = await evaluate_portfolio_alerts(
            session=session,
            user_id=99,
            portfolio_id=10,
        )
        # None 반환 시 라우터에서 404 처리
        assert result is None

    @pytest.mark.asyncio
    async def test_alert_history_returns_404_when_portfolio_not_owned(self) -> None:
        """GET /alerts/history: 소유권 불일치 시 404를 반환해야 한다."""
        from stock_picker.portfolio.portfolio_alerts import get_alert_history

        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        session = AsyncMock()
        session.execute.return_value = execute_result

        result = await get_alert_history(
            session=session,
            user_id=99,
            portfolio_id=10,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_create_value_below_alert_returns_none_when_not_owned(self) -> None:
        """POST /alerts with 'portfolio_value_below': 소유권 불일치 시 None 반환해야 한다."""
        from stock_picker.portfolio.portfolio_alerts import create_portfolio_alert

        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        session = AsyncMock()
        session.execute.return_value = execute_result

        result = await create_portfolio_alert(
            session=session,
            user_id=99,
            portfolio_id=10,
            alert_type="portfolio_value_below",
            condition_value=1_000_000.0,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_create_holding_return_alert_returns_none_when_not_owned(self) -> None:
        """POST /alerts with 'holding_return': 소유권 불일치 시 None 반환해야 한다."""
        from stock_picker.portfolio.portfolio_alerts import create_portfolio_alert

        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = None
        session = AsyncMock()
        session.execute.return_value = execute_result

        result = await create_portfolio_alert(
            session=session,
            user_id=99,
            portfolio_id=10,
            alert_type="holding_return",
            condition_value=15.0,
            target_krx_code="005930",
        )
        assert result is None


# ────────────────────────────────────────────────────────────
# 5. 서비스/통합 테스트
# ────────────────────────────────────────────────────────────


class TestAlertServiceIntegration036:
    """SPEC-036 알림 생성 서비스 통합 테스트."""

    @pytest.mark.asyncio
    async def test_create_portfolio_value_below_alert(self) -> None:
        """portfolio_value_below 타입 알림 생성이 성공해야 한다."""
        from stock_picker.portfolio.portfolio_alerts import create_portfolio_alert
        from stock_picker.db.models import Portfolio

        # 포트폴리오 소유권 확인 성공 모의
        portfolio_mock = MagicMock(spec=Portfolio)
        portfolio_mock.id = 10
        portfolio_mock.user_id = 1

        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = portfolio_mock
        session = AsyncMock()
        session.execute.return_value = execute_result
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        result = await create_portfolio_alert(
            session=session,
            user_id=1,
            portfolio_id=10,
            alert_type="portfolio_value_below",
            condition_value=1_000_000.0,
        )
        # 소유권 확인 성공 → None이 아님
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_holding_return_alert_with_krx_code(self) -> None:
        """holding_return 타입 알림 생성 시 target_krx_code가 설정되어야 한다."""
        from stock_picker.portfolio.portfolio_alerts import create_portfolio_alert
        from stock_picker.db.models import Portfolio

        portfolio_mock = MagicMock(spec=Portfolio)
        portfolio_mock.id = 10
        portfolio_mock.user_id = 1

        execute_result = MagicMock()
        execute_result.scalar_one_or_none.return_value = portfolio_mock
        session = AsyncMock()
        session.execute.return_value = execute_result
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        result = await create_portfolio_alert(
            session=session,
            user_id=1,
            portfolio_id=10,
            alert_type="holding_return",
            condition_value=15.0,
            target_krx_code="005930",
            condition_direction="above",
        )
        # 소유권 확인 성공 → None이 아님
        assert result is not None

    def test_no_scipy_in_portfolio_alerts(self) -> None:
        """portfolio_alerts.py에 scipy 임포트가 없어야 한다 (NFR-001)."""
        import ast
        import pathlib

        src_path = pathlib.Path(
            "/home/sklee/moai/ai-stock-picker/backend/src/stock_picker/portfolio/portfolio_alerts.py"
        )
        tree = ast.parse(src_path.read_text())
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        scipy_found = any("scipy" in imp for imp in imports)
        assert not scipy_found, "portfolio_alerts.py에 scipy 임포트가 있어선 안 됩니다 (NFR-001)"
