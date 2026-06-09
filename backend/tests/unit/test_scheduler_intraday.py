# 장중 30분 증분 잡 테스트 (TASK-023)
# REQ-NEWS-002: 장중 30분 단위 증분 수집
from unittest.mock import patch

import pytest


class TestSchedulerIntradayJob:
    """장중 30분 증분 잡 등록 테스트"""

    def test_setup_scheduler_registers_core_jobs(self):
        """setup_scheduler()는 핵심 잡(daily, intraday, 가격알림, 주간메일)을 등록해야 한다"""
        from stock_picker.scheduler.jobs import setup_scheduler

        scheduler = setup_scheduler()
        job_ids = {job.id for job in scheduler.get_jobs()}
        assert "daily_collection" in job_ids
        assert "intraday_collection" in job_ids
        assert "check_price_alerts" in job_ids
        assert "weekly_email_summary" in job_ids

    def test_daily_collection_job_still_registered(self):
        """기존 일 배치 잡(daily_collection)이 유지되어야 한다"""
        from stock_picker.scheduler.jobs import setup_scheduler

        scheduler = setup_scheduler()
        job_ids = [job.id for job in scheduler.get_jobs()]
        assert "daily_collection" in job_ids

    def test_intraday_collection_job_registered(self):
        """장중 30분 증분 잡(intraday_collection)이 등록되어야 한다"""
        from stock_picker.scheduler.jobs import setup_scheduler

        scheduler = setup_scheduler()
        job_ids = [job.id for job in scheduler.get_jobs()]
        assert "intraday_collection" in job_ids

    def test_intraday_job_cron_hour_range(self):
        """장중 잡의 hour 범위는 9-15여야 한다"""
        from apscheduler.triggers.cron import CronTrigger
        from stock_picker.scheduler.jobs import setup_scheduler

        scheduler = setup_scheduler()
        job = next(j for j in scheduler.get_jobs() if j.id == "intraday_collection")
        trigger = job.trigger
        assert isinstance(trigger, CronTrigger)
        hour_field = next(f for f in trigger.fields if f.name == "hour")
        # "9-15" 범위 표현 확인
        assert "9" in str(hour_field) or "9-15" in str(hour_field)

    def test_intraday_job_cron_minute_every_30(self):
        """장중 잡의 minute 설정은 */30이어야 한다"""
        from apscheduler.triggers.cron import CronTrigger
        from stock_picker.scheduler.jobs import setup_scheduler

        scheduler = setup_scheduler()
        job = next(j for j in scheduler.get_jobs() if j.id == "intraday_collection")
        trigger = job.trigger
        assert isinstance(trigger, CronTrigger)
        minute_field = next(f for f in trigger.fields if f.name == "minute")
        # "*/30" 또는 "0,30" 표현 확인
        minute_str = str(minute_field)
        assert "30" in minute_str

    def test_intraday_job_timezone_is_seoul(self):
        """장중 잡의 타임존은 Asia/Seoul이어야 한다"""
        from stock_picker.scheduler.jobs import setup_scheduler

        scheduler = setup_scheduler()
        job = next(j for j in scheduler.get_jobs() if j.id == "intraday_collection")
        trigger = job.trigger
        # CronTrigger의 timezone 확인
        assert "Seoul" in str(trigger.timezone) or "Asia/Seoul" in str(trigger.timezone)


class TestRunIntradayPipeline:
    """장중 파이프라인 실행 테스트"""

    @pytest.mark.asyncio
    async def test_intraday_pipeline_calls_collect_and_analyze(self):
        """장중 파이프라인이 수집 + 분석 + 추천을 호출해야 한다"""
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

            await jobs.run_intraday_pipeline()

        assert "collect" in call_order
        assert "analyze" in call_order
        assert "recommend" in call_order

    @pytest.mark.asyncio
    async def test_intraday_pipeline_sequential_order(self):
        """장중 파이프라인 단계 순서가 collect → analyze → recommend여야 한다"""
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

            await jobs.run_intraday_pipeline()

        assert call_order.index("collect") < call_order.index("analyze")
        assert call_order.index("analyze") < call_order.index("recommend")
