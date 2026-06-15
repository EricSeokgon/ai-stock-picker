# lifespan 내 APScheduler 연동 테스트 (SPEC-STOCK-022)
# REQ-022-SCHED-001: ENABLE_SCHEDULER=true 시 scheduler.start() 호출
# REQ-022-SCHED-002: ENABLE_SCHEDULER=false 시 scheduler 미시작
# REQ-022-SCHED-003: 스케줄러 시작 실패 시 앱은 계속 동작
import asyncio
from unittest.mock import MagicMock, patch

import pytest


async def _cancellable_loop(*args, **kwargs) -> None:
    """취소 가능한 가짜 가격 브로드캐스트 루프 (실제 asyncio.Task 사용)"""
    try:
        await asyncio.sleep(9999)
    except asyncio.CancelledError:
        raise


class TestLifespanScheduler:
    """lifespan 내 스케줄러 시작/종료 동작 테스트"""

    @pytest.mark.asyncio
    async def test_scheduler_starts_when_enabled(self, monkeypatch):
        """ENABLE_SCHEDULER=true(기본값)일 때 scheduler.start()가 호출되어야 한다"""
        monkeypatch.setenv("ENABLE_SCHEDULER", "true")

        mock_scheduler = MagicMock()
        mock_scheduler.get_jobs.return_value = [MagicMock(), MagicMock()]

        with (
            patch("stock_picker.scheduler.jobs.setup_scheduler", return_value=mock_scheduler),
            patch("stock_picker.realtime.price_broadcast.price_broadcast_loop", _cancellable_loop),
            patch("stock_picker.realtime.ws_router.manager", MagicMock()),
        ):
            from stock_picker.api.main import _lifespan
            from fastapi import FastAPI

            app = FastAPI()
            async with _lifespan(app):
                pass

        mock_scheduler.start.assert_called_once()
        mock_scheduler.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_scheduler_disabled_when_env_false(self, monkeypatch):
        """ENABLE_SCHEDULER=false 시 setup_scheduler()가 호출되지 않아야 한다"""
        monkeypatch.setenv("ENABLE_SCHEDULER", "false")

        with (
            patch("stock_picker.realtime.price_broadcast.price_broadcast_loop", _cancellable_loop),
            patch("stock_picker.realtime.ws_router.manager", MagicMock()),
            patch("stock_picker.scheduler.jobs.setup_scheduler") as mock_setup,
        ):
            from stock_picker.api.main import _lifespan
            from fastapi import FastAPI

            app = FastAPI()
            async with _lifespan(app):
                pass

        mock_setup.assert_not_called()

    @pytest.mark.asyncio
    async def test_scheduler_start_failure_does_not_crash_app(self, monkeypatch):
        """스케줄러 시작 실패 시 예외가 억제되고 앱이 정상 기동되어야 한다"""
        monkeypatch.setenv("ENABLE_SCHEDULER", "true")

        mock_scheduler = MagicMock()
        mock_scheduler.start.side_effect = RuntimeError("APScheduler 초기화 실패 (테스트)")

        with (
            patch("stock_picker.scheduler.jobs.setup_scheduler", return_value=mock_scheduler),
            patch("stock_picker.realtime.price_broadcast.price_broadcast_loop", _cancellable_loop),
            patch("stock_picker.realtime.ws_router.manager", MagicMock()),
        ):
            from stock_picker.api.main import _lifespan
            from fastapi import FastAPI

            app = FastAPI()
            # 예외 없이 lifespan이 완료되어야 한다
            async with _lifespan(app):
                pass

        # start는 시도했지만 실패 → shutdown은 호출되지 않아야 한다 (scheduler=None)
        mock_scheduler.shutdown.assert_not_called()

    @pytest.mark.asyncio
    async def test_scheduler_disabled_via_zero(self, monkeypatch):
        """ENABLE_SCHEDULER=0 시 스케줄러가 비활성화되어야 한다"""
        monkeypatch.setenv("ENABLE_SCHEDULER", "0")

        with (
            patch("stock_picker.realtime.price_broadcast.price_broadcast_loop", _cancellable_loop),
            patch("stock_picker.realtime.ws_router.manager", MagicMock()),
            patch("stock_picker.scheduler.jobs.setup_scheduler") as mock_setup,
        ):
            from stock_picker.api.main import _lifespan
            from fastapi import FastAPI

            app = FastAPI()
            async with _lifespan(app):
                pass

        mock_setup.assert_not_called()
