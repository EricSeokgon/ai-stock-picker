# 스케줄러 단위 테스트
# 실제 스케줄 실행 대신 등록 여부를 검증한다.
from unittest.mock import AsyncMock, patch

import pytest


class TestSchedulerSetup:
    def test_daily_collection_job_registered(self) -> None:
        """scheduler 시작 시 'daily_collection' 잡이 등록되어야 한다."""
        from stock_picker.scheduler.jobs import setup_scheduler

        scheduler = setup_scheduler()
        job_ids = [job.id for job in scheduler.get_jobs()]
        assert "daily_collection" in job_ids

    def test_daily_collection_cron_hour(self) -> None:
        """daily_collection 잡이 06:00 cron으로 등록되어야 한다."""
        from apscheduler.triggers.cron import CronTrigger
        from stock_picker.scheduler.jobs import setup_scheduler

        scheduler = setup_scheduler()
        job = next(j for j in scheduler.get_jobs() if j.id == "daily_collection")
        trigger = job.trigger
        assert isinstance(trigger, CronTrigger)
        # hour 필드 검증
        hour_field = next(f for f in trigger.fields if f.name == "hour")
        assert str(hour_field) == "6"

    def test_daily_collection_cron_minute(self) -> None:
        """daily_collection 잡이 분(minute)=0으로 등록되어야 한다."""
        from stock_picker.scheduler.jobs import setup_scheduler

        scheduler = setup_scheduler()
        job = next(j for j in scheduler.get_jobs() if j.id == "daily_collection")
        trigger = job.trigger
        minute_field = next(f for f in trigger.fields if f.name == "minute")
        assert str(minute_field) == "0"


class TestRunDailyPipeline:
    @pytest.mark.asyncio
    async def test_pipeline_calls_collect_all(self) -> None:
        """run_daily_pipeline 실행 시 collect_all을 호출해야 한다."""
        mock_collect = AsyncMock(return_value=[])
        mock_analyze = AsyncMock()
        mock_recommend = AsyncMock()

        with (
            patch("stock_picker.scheduler.jobs.collect_all", mock_collect),
            patch("stock_picker.scheduler.jobs.run_analysis", mock_analyze),
            patch("stock_picker.scheduler.jobs.run_recommendation", mock_recommend),
        ):
            from stock_picker.scheduler import jobs

            # 모듈 재임포트 없이 직접 패치된 상태로 실행
            await jobs.run_daily_pipeline()
            mock_collect.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_calls_analysis_after_collect(self) -> None:
        """collect_all 이후 run_analysis가 호출되어야 한다."""
        call_order: list[str] = []

        async def fake_collect() -> list:
            call_order.append("collect")
            return []

        async def fake_analyze() -> None:
            call_order.append("analyze")

        async def fake_recommend() -> None:
            call_order.append("recommend")

        with (
            patch("stock_picker.scheduler.jobs.collect_all", fake_collect),
            patch("stock_picker.scheduler.jobs.run_analysis", fake_analyze),
            patch("stock_picker.scheduler.jobs.run_recommendation", fake_recommend),
        ):
            from stock_picker.scheduler import jobs

            await jobs.run_daily_pipeline()
            # 순서 검증
            assert call_order.index("collect") < call_order.index("analyze")
            assert call_order.index("analyze") < call_order.index("recommend")

    @pytest.mark.asyncio
    async def test_pipeline_calls_recommendation_last(self) -> None:
        """run_recommendation이 파이프라인 마지막에 호출되어야 한다."""
        call_order: list[str] = []

        async def fake_collect() -> list:
            call_order.append("collect")
            return []

        async def fake_analyze() -> None:
            call_order.append("analyze")

        async def fake_recommend() -> None:
            call_order.append("recommend")

        with (
            patch("stock_picker.scheduler.jobs.collect_all", fake_collect),
            patch("stock_picker.scheduler.jobs.run_analysis", fake_analyze),
            patch("stock_picker.scheduler.jobs.run_recommendation", fake_recommend),
        ):
            from stock_picker.scheduler import jobs

            await jobs.run_daily_pipeline()
            assert call_order[-1] == "recommend"
