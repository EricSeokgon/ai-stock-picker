"""포트폴리오 알림 강화 단위 테스트 (SPEC-STOCK-031).

TDD RED 단계: 구현 전 먼저 작성하여 실패 확인 후 GREEN으로 구현.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ────────────────────────────────────────────────────────────
# 테스트용 헬퍼 객체
# ────────────────────────────────────────────────────────────


def _make_period(
    has_data: bool = True,
    total_return_pct: float | None = 12.0,
    mdd_pct: float | None = -5.0,
) -> Any:
    """PerformanceSummaryResponse.periods[0] 형태 모의 객체 생성."""
    period = MagicMock()
    period.has_data = has_data
    period.total_return_pct = total_return_pct
    period.mdd_pct = mdd_pct
    return period


def _make_performance(period: Any | None = None) -> Any:
    """PerformanceSummaryResponse 형태 모의 객체 생성."""
    perf = MagicMock()
    perf.periods = [period or _make_period()]
    return perf


def _make_alert(
    id: int = 1,
    user_id: int = 1,
    portfolio_id: int = 10,
    alert_type: str = "portfolio_target_return",
    condition_value: float = 10.0,
    is_active: bool = True,
    is_triggered: bool = False,
) -> Any:
    """PortfolioAlert ORM 모의 객체 생성."""
    alert = MagicMock()
    alert.id = id
    alert.user_id = user_id
    alert.portfolio_id = portfolio_id
    alert.alert_type = alert_type
    alert.condition_value = condition_value
    alert.is_active = is_active
    alert.is_triggered = is_triggered
    return alert


# ────────────────────────────────────────────────────────────
# 1. 순수 함수 테스트: check_portfolio_return_alert
# ────────────────────────────────────────────────────────────


class TestCheckPortfolioReturnAlert:
    """포트폴리오 목표 수익률 도달 조건 평가 (REQ-PAL-002)."""

    def test_triggers_when_return_exceeds_target(self) -> None:
        """YTD 수익률 ≥ 목표값이면 발화해야 한다 (Scenario 1)."""
        from stock_picker.portfolio.portfolio_alerts import check_portfolio_return_alert

        alert = _make_alert(condition_value=10.0)
        performance = _make_performance(_make_period(has_data=True, total_return_pct=12.0))

        triggered, msg = check_portfolio_return_alert(alert, performance)

        assert triggered is True
        assert "12.00" in msg
        assert "10.00" in msg

    def test_triggers_when_return_equals_target(self) -> None:
        """YTD 수익률 == 목표값(경계)이면 발화해야 한다."""
        from stock_picker.portfolio.portfolio_alerts import check_portfolio_return_alert

        alert = _make_alert(condition_value=10.0)
        performance = _make_performance(_make_period(has_data=True, total_return_pct=10.0))

        triggered, msg = check_portfolio_return_alert(alert, performance)

        assert triggered is True

    def test_no_trigger_when_return_below_target(self) -> None:
        """YTD 수익률 < 목표값이면 발화하지 않아야 한다."""
        from stock_picker.portfolio.portfolio_alerts import check_portfolio_return_alert

        alert = _make_alert(condition_value=10.0)
        performance = _make_performance(_make_period(has_data=True, total_return_pct=5.0))

        triggered, msg = check_portfolio_return_alert(alert, performance)

        assert triggered is False
        assert msg == ""

    def test_no_trigger_when_has_data_false(self) -> None:
        """has_data=False이면 발화하지 않아야 한다 (Scenario 3 응용)."""
        from stock_picker.portfolio.portfolio_alerts import check_portfolio_return_alert

        alert = _make_alert(condition_value=10.0)
        performance = _make_performance(_make_period(has_data=False, total_return_pct=12.0))

        triggered, msg = check_portfolio_return_alert(alert, performance)

        assert triggered is False
        assert msg == ""

    def test_no_trigger_when_total_return_pct_is_none(self) -> None:
        """total_return_pct=None이면 발화하지 않아야 한다."""
        from stock_picker.portfolio.portfolio_alerts import check_portfolio_return_alert

        alert = _make_alert(condition_value=10.0)
        performance = _make_performance(_make_period(has_data=True, total_return_pct=None))

        triggered, msg = check_portfolio_return_alert(alert, performance)

        assert triggered is False
        assert msg == ""


# ────────────────────────────────────────────────────────────
# 2. 순수 함수 테스트: check_portfolio_mdd_alert
# ────────────────────────────────────────────────────────────


class TestCheckPortfolioMddAlert:
    """포트폴리오 MDD 임계값 초과 조건 평가 (REQ-PAL-003)."""

    def test_triggers_when_mdd_exceeds_threshold(self) -> None:
        """YTD MDD ≤ 임계값(더 큰 낙폭)이면 발화해야 한다 (Scenario 2)."""
        from stock_picker.portfolio.portfolio_alerts import check_portfolio_mdd_alert

        alert = _make_alert(alert_type="portfolio_mdd_breach", condition_value=-15.0)
        performance = _make_performance(_make_period(has_data=True, mdd_pct=-16.5))

        triggered, msg = check_portfolio_mdd_alert(alert, performance)

        assert triggered is True
        assert "-16.50" in msg
        assert "-15.00" in msg

    def test_triggers_when_mdd_equals_threshold(self) -> None:
        """YTD MDD == 임계값(경계)이면 발화해야 한다."""
        from stock_picker.portfolio.portfolio_alerts import check_portfolio_mdd_alert

        alert = _make_alert(alert_type="portfolio_mdd_breach", condition_value=-15.0)
        performance = _make_performance(_make_period(has_data=True, mdd_pct=-15.0))

        triggered, msg = check_portfolio_mdd_alert(alert, performance)

        assert triggered is True

    def test_no_trigger_when_mdd_below_threshold(self) -> None:
        """YTD MDD > 임계값(낙폭 미달)이면 발화하지 않아야 한다."""
        from stock_picker.portfolio.portfolio_alerts import check_portfolio_mdd_alert

        alert = _make_alert(alert_type="portfolio_mdd_breach", condition_value=-15.0)
        performance = _make_performance(_make_period(has_data=True, mdd_pct=-5.0))

        triggered, msg = check_portfolio_mdd_alert(alert, performance)

        assert triggered is False
        assert msg == ""

    def test_no_trigger_when_has_data_false(self) -> None:
        """has_data=False이면 발화하지 않아야 한다."""
        from stock_picker.portfolio.portfolio_alerts import check_portfolio_mdd_alert

        alert = _make_alert(alert_type="portfolio_mdd_breach", condition_value=-15.0)
        performance = _make_performance(_make_period(has_data=False, mdd_pct=-16.5))

        triggered, msg = check_portfolio_mdd_alert(alert, performance)

        assert triggered is False
        assert msg == ""

    def test_no_trigger_when_mdd_pct_is_none(self) -> None:
        """mdd_pct=None이면 발화하지 않아야 한다."""
        from stock_picker.portfolio.portfolio_alerts import check_portfolio_mdd_alert

        alert = _make_alert(alert_type="portfolio_mdd_breach", condition_value=-15.0)
        performance = _make_performance(_make_period(has_data=True, mdd_pct=None))

        triggered, msg = check_portfolio_mdd_alert(alert, performance)

        assert triggered is False
        assert msg == ""


# ────────────────────────────────────────────────────────────
# 3. 오케스트레이션 테스트: check_all_portfolio_alerts
# ────────────────────────────────────────────────────────────


class TestCheckAllPortfolioAlerts:
    """포트폴리오 알림 일괄 점검 오케스트레이션 (REQ-PAL-004)."""

    @pytest.mark.asyncio
    async def test_triggers_return_alert_and_updates_db(self) -> None:
        """목표 수익률 도달 시 is_triggered=True 업데이트 및 notifications 적재."""
        from stock_picker.portfolio.portfolio_alerts import check_all_portfolio_alerts

        session = AsyncMock()
        # 활성 미발화 알림 1개 반환
        alert = _make_alert(id=1, alert_type="portfolio_target_return", condition_value=10.0)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [alert]
        session.execute = AsyncMock(return_value=mock_result)

        performance = _make_performance(_make_period(has_data=True, total_return_pct=12.0))

        with patch(
            "stock_picker.portfolio.portfolio_alerts.calculate_performance_summary",
            new=AsyncMock(return_value=performance),
        ), patch(
            "stock_picker.portfolio.portfolio_alerts.is_channel_enabled_async",
            new=AsyncMock(return_value=False),
        ):
            count = await check_all_portfolio_alerts(session)

        assert count == 1
        # commit이 호출되었는지 확인
        session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_skips_already_triggered_alert(self) -> None:
        """is_triggered=True인 알림은 평가 제외해야 한다 (Scenario 3, 멱등성)."""
        from stock_picker.portfolio.portfolio_alerts import check_all_portfolio_alerts

        session = AsyncMock()
        # 이미 발화된 알림은 WHERE is_triggered=False 조건으로 필터되어 빈 목록 반환
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        count = await check_all_portfolio_alerts(session)

        assert count == 0

    @pytest.mark.asyncio
    async def test_skips_inactive_alert(self) -> None:
        """is_active=False인 알림은 평가 제외해야 한다 (Scenario 6)."""
        from stock_picker.portfolio.portfolio_alerts import check_all_portfolio_alerts

        session = AsyncMock()
        # is_active=False 알림은 WHERE is_active=True 조건으로 필터되어 빈 목록 반환
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        count = await check_all_portfolio_alerts(session)

        assert count == 0

    @pytest.mark.asyncio
    async def test_graceful_on_performance_error(self) -> None:
        """성과 조회 실패 시 예외가 전파되지 않아야 한다 (NFR-004)."""
        from stock_picker.portfolio.portfolio_alerts import check_all_portfolio_alerts

        session = AsyncMock()
        alert = _make_alert(id=1)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [alert]
        session.execute = AsyncMock(return_value=mock_result)

        with patch(
            "stock_picker.portfolio.portfolio_alerts.calculate_performance_summary",
            new=AsyncMock(side_effect=Exception("성과 조회 실패")),
        ):
            # 예외가 전파되지 않고 0 반환
            count = await check_all_portfolio_alerts(session)

        assert count == 0

    @pytest.mark.asyncio
    async def test_performance_summary_called_once_per_portfolio(self) -> None:
        """동일 포트폴리오의 2개 알림 점검 시 성과 요약 1회만 조회해야 한다 (NFR-002)."""
        from stock_picker.portfolio.portfolio_alerts import check_all_portfolio_alerts

        session = AsyncMock()
        # 동일 포트폴리오(id=10)에 2개 알림
        alerts = [
            _make_alert(id=1, portfolio_id=10, alert_type="portfolio_target_return", condition_value=10.0),
            _make_alert(id=2, portfolio_id=10, alert_type="portfolio_mdd_breach", condition_value=-15.0),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = alerts
        session.execute = AsyncMock(return_value=mock_result)

        performance = _make_performance(
            _make_period(has_data=True, total_return_pct=12.0, mdd_pct=-16.5)
        )

        mock_calculate = AsyncMock(return_value=performance)
        with patch(
            "stock_picker.portfolio.portfolio_alerts.calculate_performance_summary",
            new=mock_calculate,
        ), patch(
            "stock_picker.portfolio.portfolio_alerts.is_channel_enabled_async",
            new=AsyncMock(return_value=False),
        ):
            count = await check_all_portfolio_alerts(session)

        # 성과 요약 1회만 호출 (NFR-002)
        assert mock_calculate.call_count == 1
        assert count == 2

    @pytest.mark.asyncio
    async def test_no_email_when_channel_disabled(self) -> None:
        """이메일 채널 비활성 시 실제 이메일 발송하지 않아야 한다 (Scenario 5, REQ-PAL-006)."""
        from stock_picker.portfolio.portfolio_alerts import check_all_portfolio_alerts

        session = AsyncMock()
        alert = _make_alert(id=1, alert_type="portfolio_target_return", condition_value=10.0)
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [alert]
        session.execute = AsyncMock(return_value=mock_result)

        performance = _make_performance(_make_period(has_data=True, total_return_pct=12.0))

        with patch(
            "stock_picker.portfolio.portfolio_alerts.calculate_performance_summary",
            new=AsyncMock(return_value=performance),
        ), patch(
            "stock_picker.portfolio.portfolio_alerts.is_channel_enabled_async",
            new=AsyncMock(return_value=False),
        ):
            count = await check_all_portfolio_alerts(session)

        # 채널 비활성 → 알림은 발화(인박스 적재)되지만 이메일 미발송
        assert count == 1


# ────────────────────────────────────────────────────────────
# 4. CRUD 서비스 테스트
# ────────────────────────────────────────────────────────────


class TestPortfolioAlertCrud:
    """포트폴리오 알림 CRUD 서비스 테스트 (REQ-PAL-001, REQ-PAL-008, NFR-005)."""

    @pytest.mark.asyncio
    async def test_create_alert_returns_alert(self) -> None:
        """알림 생성 시 생성된 PortfolioAlert 반환해야 한다."""
        from stock_picker.portfolio.portfolio_alerts import create_portfolio_alert

        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        # 소유권 확인 — 포트폴리오 존재
        portfolio = MagicMock()
        portfolio.user_id = 1
        portfolio_result = MagicMock()
        portfolio_result.scalar_one_or_none.return_value = portfolio
        session.execute = AsyncMock(return_value=portfolio_result)

        result = await create_portfolio_alert(
            session=session,
            user_id=1,
            portfolio_id=10,
            alert_type="portfolio_target_return",
            condition_value=10.0,
        )

        assert result is not None
        session.add.assert_called_once()
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_alert_returns_none_when_portfolio_not_owned(self) -> None:
        """소유권 불일치 시 None 반환해야 한다 (→ 404, Scenario 4, NFR-005)."""
        from stock_picker.portfolio.portfolio_alerts import create_portfolio_alert

        session = AsyncMock()
        # 포트폴리오 없음 (소유권 불일치)
        portfolio_result = MagicMock()
        portfolio_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=portfolio_result)

        result = await create_portfolio_alert(
            session=session,
            user_id=1,
            portfolio_id=10,
            alert_type="portfolio_target_return",
            condition_value=10.0,
        )

        assert result is None
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_list_alerts_returns_list(self) -> None:
        """포트폴리오 알림 목록 조회해야 한다."""
        from stock_picker.portfolio.portfolio_alerts import list_portfolio_alerts

        session = AsyncMock()
        alerts = [_make_alert(id=1), _make_alert(id=2)]
        result = MagicMock()
        result.scalars.return_value.all.return_value = alerts

        # 소유권 확인 포트폴리오 조회 + 알림 목록 조회 순서
        portfolio_result = MagicMock()
        portfolio_result.scalar_one_or_none.return_value = MagicMock(user_id=1)
        session.execute = AsyncMock(side_effect=[portfolio_result, result])

        found = await list_portfolio_alerts(session=session, user_id=1, portfolio_id=10)

        assert len(found) == 2

    @pytest.mark.asyncio
    async def test_list_alerts_returns_none_when_not_owned(self) -> None:
        """소유권 불일치 시 None 반환해야 한다."""
        from stock_picker.portfolio.portfolio_alerts import list_portfolio_alerts

        session = AsyncMock()
        portfolio_result = MagicMock()
        portfolio_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=portfolio_result)

        found = await list_portfolio_alerts(session=session, user_id=1, portfolio_id=10)

        assert found is None

    @pytest.mark.asyncio
    async def test_update_alert_updates_fields(self) -> None:
        """알림 수정 시 condition_value, is_active 업데이트해야 한다."""
        from stock_picker.portfolio.portfolio_alerts import update_portfolio_alert

        session = AsyncMock()
        existing_alert = _make_alert(id=1, condition_value=10.0, is_active=True)

        # 소유권 확인 → 알림 조회
        alert_result = MagicMock()
        alert_result.scalar_one_or_none.return_value = existing_alert
        session.execute = AsyncMock(return_value=alert_result)

        updated = await update_portfolio_alert(
            session=session,
            user_id=1,
            portfolio_id=10,
            alert_id=1,
            condition_value=20.0,
            is_active=False,
        )

        assert updated is not None
        assert existing_alert.condition_value == 20.0
        assert existing_alert.is_active is False

    @pytest.mark.asyncio
    async def test_delete_alert_removes_alert(self) -> None:
        """알림 삭제 시 True 반환해야 한다."""
        from stock_picker.portfolio.portfolio_alerts import delete_portfolio_alert

        session = AsyncMock()
        existing_alert = _make_alert(id=1)
        alert_result = MagicMock()
        alert_result.scalar_one_or_none.return_value = existing_alert
        session.execute = AsyncMock(return_value=alert_result)

        deleted = await delete_portfolio_alert(
            session=session, user_id=1, portfolio_id=10, alert_id=1
        )

        assert deleted is True
        session.delete.assert_called_once_with(existing_alert)

    @pytest.mark.asyncio
    async def test_delete_alert_returns_false_when_not_found(self) -> None:
        """존재하지 않는 알림 삭제 시 False 반환해야 한다."""
        from stock_picker.portfolio.portfolio_alerts import delete_portfolio_alert

        session = AsyncMock()
        alert_result = MagicMock()
        alert_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=alert_result)

        deleted = await delete_portfolio_alert(
            session=session, user_id=1, portfolio_id=10, alert_id=999
        )

        assert deleted is False
        session.delete.assert_not_called()


# ────────────────────────────────────────────────────────────
# 5. scipy 미사용 검증
# ────────────────────────────────────────────────────────────


class TestNoScipyImport:
    """NFR-001: portfolio_alerts.py에 scipy import가 없어야 한다."""

    def test_no_scipy_in_portfolio_alerts(self) -> None:
        """portfolio_alerts.py 소스 코드에 'scipy' 문자열 없어야 한다."""
        import importlib.util
        import pathlib

        src_path = pathlib.Path(__file__).parent.parent.parent / "src" / "stock_picker" / "portfolio" / "portfolio_alerts.py"
        if not src_path.exists():
            pytest.skip("portfolio_alerts.py 아직 생성 전 (RED 단계)")

        content = src_path.read_text()
        assert "scipy" not in content, "portfolio_alerts.py에 scipy import가 있어서는 안 됩니다 (NFR-001)"
