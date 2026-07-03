"""포트폴리오 목표 관리 단위 테스트 (SPEC-STOCK-041).

TDD RED 단계: 구현 전 먼저 작성 — 초기 실행 시 ImportError/AssertionError 예상.
GREEN 단계에서 goals.py, schemas.py, router.py, jobs.py를 구현해 통과시킨다.

테스트 실행:
    cd /home/sklee/moai/ai-stock-picker/backend
    python -m pytest tests/unit/test_portfolio_goal_041.py -v
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# 헬퍼: 모의 PortfolioGoal ORM 객체 생성
# ─────────────────────────────────────────────────────────────────────────────


def _make_goal(
    id: int = 1,
    portfolio_id: int = 10,
    target_amount: float | None = 10_000_000.0,
    target_return_rate: float | None = None,
    deadline: date | None = None,
    is_active: bool = True,
    goal_reached_notified: bool = False,
) -> Any:
    """PortfolioGoal ORM 모의 객체 생성."""
    goal = MagicMock()
    goal.id = id
    goal.portfolio_id = portfolio_id
    goal.target_amount = Decimal(str(target_amount)) if target_amount is not None else None
    goal.target_return_rate = Decimal(str(target_return_rate)) if target_return_rate is not None else None
    goal.deadline = deadline
    goal.is_active = is_active
    goal.goal_reached_notified = goal_reached_notified
    return goal


def _make_portfolio(id: int = 10, user_id: int = 1) -> Any:
    """Portfolio ORM 모의 객체 생성."""
    p = MagicMock()
    p.id = id
    p.user_id = user_id
    return p


# ─────────────────────────────────────────────────────────────────────────────
# 스키마 단위 테스트 (Pydantic v2)
# ─────────────────────────────────────────────────────────────────────────────


class TestGoalCreateSchema:
    """GoalCreate Pydantic 스키마 검증 (REQ-GOAL-001, REQ-GOAL-012, REQ-GOAL-013a)."""

    def test_T001_amount_only_valid(self) -> None:
        """T-001: target_amount만 설정 → 유효한 스키마."""
        from stock_picker.portfolio.schemas import GoalCreate

        g = GoalCreate(target_amount=Decimal("10000000.00"))
        assert g.target_amount == Decimal("10000000.00")
        assert g.target_return_rate is None

    def test_T002_return_rate_only_valid(self) -> None:
        """T-002: target_return_rate만 설정 → 유효한 스키마."""
        from stock_picker.portfolio.schemas import GoalCreate

        g = GoalCreate(target_return_rate=Decimal("15.0"))
        assert g.target_return_rate == Decimal("15.0")
        assert g.target_amount is None

    def test_T003_all_fields_valid(self) -> None:
        """T-003: target_amount + target_return_rate + deadline 모두 설정 → 유효."""
        from stock_picker.portfolio.schemas import GoalCreate

        g = GoalCreate(
            target_amount=Decimal("5000000.00"),
            target_return_rate=Decimal("20.0"),
            deadline=date(2026, 12, 31),
        )
        assert g.deadline == date(2026, 12, 31)

    def test_T012_deadline_only_raises_422(self) -> None:
        """T-012: deadline만 설정 (amount도 rate도 없음) → ValidationError."""
        from pydantic import ValidationError

        from stock_picker.portfolio.schemas import GoalCreate

        with pytest.raises(ValidationError):
            GoalCreate(deadline=date(2026, 12, 31))

    def test_T013a_target_amount_zero_raises_422(self) -> None:
        """T-013a: target_amount=0 → ValidationError."""
        from pydantic import ValidationError

        from stock_picker.portfolio.schemas import GoalCreate

        with pytest.raises(ValidationError):
            GoalCreate(target_amount=Decimal("0"))

    def test_T013a_target_amount_negative_raises_422(self) -> None:
        """T-013a: target_amount 음수 → ValidationError."""
        from pydantic import ValidationError

        from stock_picker.portfolio.schemas import GoalCreate

        with pytest.raises(ValidationError):
            GoalCreate(target_amount=Decimal("-100"))

    def test_T013a_target_return_rate_zero_raises_422(self) -> None:
        """T-013a: target_return_rate=0 → ValidationError."""
        from pydantic import ValidationError

        from stock_picker.portfolio.schemas import GoalCreate

        with pytest.raises(ValidationError):
            GoalCreate(target_return_rate=Decimal("0"))


# ─────────────────────────────────────────────────────────────────────────────
# 서비스 함수 단위 테스트 (goals.py)
# ─────────────────────────────────────────────────────────────────────────────


class TestCalculateAchievementRate:
    """achievement_rate 계산 로직 (REQ-GOAL-006)."""

    def test_T004_amount_only_calculation(self) -> None:
        """T-004: amount만 설정 → (current_value / target_amount) * 100."""
        from stock_picker.portfolio.goals import calculate_achievement_rate

        rate = calculate_achievement_rate(
            current_value=8_000_000.0,
            current_return_rate=0.0,
            target_amount=Decimal("10000000.00"),
            target_return_rate=None,
        )
        assert rate == pytest.approx(80.0, abs=0.01)

    def test_T005_rate_only_calculation(self) -> None:
        """T-005: rate만 설정 → (current_return_rate / target_return_rate) * 100."""
        from stock_picker.portfolio.goals import calculate_achievement_rate

        rate = calculate_achievement_rate(
            current_value=0.0,
            current_return_rate=10.0,
            target_amount=None,
            target_return_rate=Decimal("20.0"),
        )
        assert rate == pytest.approx(50.0, abs=0.01)

    def test_T006_both_set_returns_min(self) -> None:
        """T-006: 둘 다 설정 → MIN 적용."""
        from stock_picker.portfolio.goals import calculate_achievement_rate

        # amount 달성률: (8_000_000 / 10_000_000) * 100 = 80.0
        # rate 달성률: (5 / 20) * 100 = 25.0 → MIN = 25.0
        rate = calculate_achievement_rate(
            current_value=8_000_000.0,
            current_return_rate=5.0,
            target_amount=Decimal("10000000.00"),
            target_return_rate=Decimal("20.0"),
        )
        assert rate == pytest.approx(25.0, abs=0.01)

    def test_T015_negative_return_rate_clamps_to_zero(self) -> None:
        """T-015: current_return_rate 음수 → achievement_rate >= 0.0 (클램프)."""
        from stock_picker.portfolio.goals import calculate_achievement_rate

        rate = calculate_achievement_rate(
            current_value=0.0,
            current_return_rate=-5.0,
            target_amount=None,
            target_return_rate=Decimal("20.0"),
        )
        assert rate == 0.0

    def test_T013b_invalid_target_amount_in_db_returns_zero(self) -> None:
        """T-013b: target_amount <= 0 (DB 행 이상) → 0.0 반환 (division-by-zero 방어)."""
        from stock_picker.portfolio.goals import calculate_achievement_rate

        rate = calculate_achievement_rate(
            current_value=1_000_000.0,
            current_return_rate=0.0,
            target_amount=Decimal("0"),
            target_return_rate=None,
        )
        assert rate == 0.0


class TestGetGoalProgress:
    """get_goal_progress 서비스 함수 (days_remaining 포함)."""

    def test_T011_past_deadline_days_remaining_zero(self) -> None:
        """T-011: deadline이 과거 → days_remaining=0 (음수 없음)."""
        from stock_picker.portfolio.goals import get_days_remaining

        past_date = date.today() - timedelta(days=10)
        assert get_days_remaining(past_date) == 0

    def test_future_deadline_returns_positive(self) -> None:
        """미래 deadline → 양수 days_remaining."""
        from stock_picker.portfolio.goals import get_days_remaining

        future_date = date.today() + timedelta(days=30)
        result = get_days_remaining(future_date)
        assert result > 0

    def test_none_deadline_returns_none(self) -> None:
        """deadline=None → None 반환."""
        from stock_picker.portfolio.goals import get_days_remaining

        assert get_days_remaining(None) is None


# ─────────────────────────────────────────────────────────────────────────────
# 라우터 단위 테스트 (DB 목업)
# ─────────────────────────────────────────────────────────────────────────────


class TestGoalRouterCreate:
    """POST /portfolios/{portfolio_id}/goals (REQ-GOAL-001, REQ-GOAL-001a, REQ-GOAL-004)."""

    def _make_db(self, portfolio: Any = None, existing_goal: Any = None) -> MagicMock:
        """모의 DB 세션 생성."""
        db = MagicMock()
        query_mock = MagicMock()
        filter_mock = MagicMock()

        # 포트폴리오 소유권 쿼리
        if portfolio is not None:
            filter_mock.first.return_value = portfolio
        else:
            filter_mock.first.return_value = None

        query_mock.filter.return_value = filter_mock
        db.query.return_value = query_mock
        return db

    def test_T007_non_owner_returns_404(self) -> None:
        """T-007: 비소유자 접근 → 404 (owner 없음 분기)."""
        from fastapi import HTTPException

        from stock_picker.portfolio.goals import create_goal

        db = self._make_db(portfolio=None)
        user = MagicMock()
        user.id = 99

        with pytest.raises(HTTPException) as exc_info:
            create_goal(db, portfolio_id=10, user_id=99, target_amount=Decimal("1000000"))
        assert exc_info.value.status_code == 404

    def test_T014_duplicate_active_goal_returns_409(self) -> None:
        """T-014: 이미 활성 목표 존재 → 409 Conflict."""
        from fastapi import HTTPException

        from stock_picker.portfolio.goals import create_goal

        portfolio = _make_portfolio(id=10, user_id=1)
        existing_goal = _make_goal(id=5, portfolio_id=10)

        db = MagicMock()

        def _side_effect_query(model):
            q = MagicMock()
            f = MagicMock()
            # 포트폴리오 소유권 확인 → 반환
            # 활성 목표 조회 → 기존 목표 반환
            # 모델 타입으로 분기
            from stock_picker.db.models import Portfolio, PortfolioGoal

            if model is Portfolio:
                f.first.return_value = portfolio
            elif model is PortfolioGoal:
                f.first.return_value = existing_goal
            else:
                f.first.return_value = None
            q.filter.return_value = f
            return q

        db.query.side_effect = _side_effect_query

        with pytest.raises(HTTPException) as exc_info:
            create_goal(db, portfolio_id=10, user_id=1, target_amount=Decimal("1000000"))
        assert exc_info.value.status_code == 409

    def test_T001_create_with_amount_only_returns_goal(self) -> None:
        """T-001: target_amount만 설정 → Goal 객체 반환."""
        from stock_picker.db.models import PortfolioGoal
        from stock_picker.portfolio.goals import create_goal

        portfolio = _make_portfolio(id=10, user_id=1)

        db = MagicMock()

        def _side_effect_query(model):
            q = MagicMock()
            f = MagicMock()
            from stock_picker.db.models import Portfolio, PortfolioGoal

            if model is Portfolio:
                f.first.return_value = portfolio
            elif model is PortfolioGoal:
                f.first.return_value = None  # 기존 목표 없음
            else:
                f.first.return_value = None
            q.filter.return_value = f
            return q

        db.query.side_effect = _side_effect_query
        db.add = MagicMock()
        db.commit = MagicMock()
        db.refresh = MagicMock(side_effect=lambda obj: obj)

        result = create_goal(db, portfolio_id=10, user_id=1, target_amount=Decimal("10000000"))
        # add, commit, refresh 호출 확인
        assert db.add.called
        assert db.commit.called
        # T-001 핵심 검증: 반환된 Goal 객체에 target_amount가 설정되어 있어야 한다
        assert isinstance(result, PortfolioGoal)
        assert result.portfolio_id == 10
        assert result.target_amount == Decimal("10000000")
        assert result.target_return_rate is None

    def test_T002_create_with_return_rate_only_returns_goal(self) -> None:
        """T-002: target_return_rate만 설정 → Goal 객체 반환."""
        from stock_picker.db.models import PortfolioGoal
        from stock_picker.portfolio.goals import create_goal

        portfolio = _make_portfolio(id=10, user_id=1)

        db = MagicMock()

        def _side_effect_query(model):
            q = MagicMock()
            f = MagicMock()
            from stock_picker.db.models import Portfolio, PortfolioGoal

            if model is Portfolio:
                f.first.return_value = portfolio
            elif model is PortfolioGoal:
                f.first.return_value = None
            else:
                f.first.return_value = None
            q.filter.return_value = f
            return q

        db.query.side_effect = _side_effect_query
        db.add = MagicMock()
        db.commit = MagicMock()
        db.refresh = MagicMock(side_effect=lambda obj: obj)

        result = create_goal(db, portfolio_id=10, user_id=1, target_return_rate=Decimal("15.0"))
        assert db.add.called
        assert db.commit.called
        # T-002 핵심 검증: 반환된 Goal 객체에 target_return_rate가 설정되어 있어야 한다
        assert isinstance(result, PortfolioGoal)
        assert result.portfolio_id == 10
        assert result.target_return_rate == Decimal("15.0")
        assert result.target_amount is None


class TestGoalRouterGet:
    """GET /portfolios/{portfolio_id}/goals (REQ-GOAL-002, REQ-GOAL-005)."""

    def test_T008_no_active_goal_returns_none(self) -> None:
        """T-008: 활성 목표 없음 → None 반환 (204 처리용)."""
        from stock_picker.portfolio.goals import get_active_goal

        portfolio = _make_portfolio(id=10, user_id=1)

        db = MagicMock()

        def _side_effect_query(model):
            q = MagicMock()
            f = MagicMock()
            from stock_picker.db.models import Portfolio, PortfolioGoal

            if model is Portfolio:
                f.first.return_value = portfolio
            elif model is PortfolioGoal:
                f.first.return_value = None
            else:
                f.first.return_value = None
            q.filter.return_value = f
            return q

        db.query.side_effect = _side_effect_query

        result = get_active_goal(db, portfolio_id=10, user_id=1)
        assert result is None

    def test_T007_get_non_owner_returns_404(self) -> None:
        """T-007: 비소유자 GET → 404."""
        from fastapi import HTTPException

        from stock_picker.portfolio.goals import get_active_goal

        db = MagicMock()

        def _side_effect_query(model):
            q = MagicMock()
            f = MagicMock()
            from stock_picker.db.models import Portfolio

            if model is Portfolio:
                f.first.return_value = None
            else:
                f.first.return_value = None
            q.filter.return_value = f
            return q

        db.query.side_effect = _side_effect_query

        with pytest.raises(HTTPException) as exc_info:
            get_active_goal(db, portfolio_id=10, user_id=99)
        assert exc_info.value.status_code == 404


class TestGoalRouterDelete:
    """DELETE /portfolios/{portfolio_id}/goals/{goal_id} (REQ-GOAL-003, REQ-GOAL-004)."""

    def test_T009_delete_sets_is_active_false(self) -> None:
        """T-009: DELETE → goal.is_active=False (소프트 삭제), True 반환."""
        from stock_picker.portfolio.goals import delete_goal

        portfolio = _make_portfolio(id=10, user_id=1)
        goal = _make_goal(id=1, portfolio_id=10, is_active=True)

        db = MagicMock()

        def _side_effect_query(model):
            q = MagicMock()
            f = MagicMock()
            from stock_picker.db.models import Portfolio, PortfolioGoal

            if model is Portfolio:
                f.first.return_value = portfolio
            elif model is PortfolioGoal:
                f.first.return_value = goal
            else:
                f.first.return_value = None
            q.filter.return_value = f
            return q

        db.query.side_effect = _side_effect_query
        db.commit = MagicMock()

        result = delete_goal(db, portfolio_id=10, goal_id=1, user_id=1)
        assert result is True
        assert goal.is_active is False
        assert db.commit.called

    def test_T007_delete_non_owner_returns_404(self) -> None:
        """T-007: 비소유자 DELETE → 404."""
        from fastapi import HTTPException

        from stock_picker.portfolio.goals import delete_goal

        db = MagicMock()

        def _side_effect_query(model):
            q = MagicMock()
            f = MagicMock()
            from stock_picker.db.models import Portfolio

            if model is Portfolio:
                f.first.return_value = None
            else:
                f.first.return_value = None
            q.filter.return_value = f
            return q

        db.query.side_effect = _side_effect_query

        with pytest.raises(HTTPException) as exc_info:
            delete_goal(db, portfolio_id=10, goal_id=1, user_id=99)
        assert exc_info.value.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# 스케줄러 단위 테스트 (T-010)
# ─────────────────────────────────────────────────────────────────────────────


class TestCheckPortfolioGoals:
    """check_portfolio_goals() 스케줄러 함수 (REQ-GOAL-007)."""

    @pytest.mark.asyncio
    async def test_T010_sends_notification_once_and_marks_notified(self) -> None:
        """T-010: achievement_rate >= 100, goal_reached_notified=False
        → 텔레그램+이메일 각 1회 발송, goal_reached_notified=True 설정, 멱등성 보장.
        """
        from stock_picker.scheduler.jobs import check_portfolio_goals

        # 목표 달성 목표 (100% 이상, 아직 알림 미발송)
        goal = _make_goal(
            id=1,
            portfolio_id=10,
            target_amount=5_000_000.0,
            goal_reached_notified=False,
        )

        mock_session = MagicMock()

        # PortfolioGoal 전체 목록 조회
        scalars_result = MagicMock()
        scalars_result.all.return_value = [goal]

        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_result

        mock_session.execute = AsyncMock(return_value=execute_result)
        mock_session.commit = AsyncMock()

        # AsyncSessionLocal 컨텍스트 매니저 모킹
        mock_async_session_cls = MagicMock()
        mock_async_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_async_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("stock_picker.scheduler.jobs.AsyncSessionLocal", mock_async_session_cls),
            patch(
                "stock_picker.scheduler.jobs.calculate_performance",
                new=AsyncMock(
                    return_value={
                        "total_current": 6_000_000.0,  # 120% 달성
                        "total_return_pct": 25.0,
                    }
                ),
            ),
            patch(
                "stock_picker.scheduler.jobs._send_message_sync",
            ) as mock_tg,
            patch(
                "stock_picker.scheduler.jobs.send_general_alert_email",
            ) as mock_email,
            patch("stock_picker.scheduler.jobs.get_user_for_portfolio", return_value=MagicMock(
                id=1, email="test@example.com", username="tester"
            )),
            patch("stock_picker.scheduler.jobs.get_user_telegram_chat_id", return_value="chat123"),
        ):
            await check_portfolio_goals()

        # 각각 1회씩 호출됐는지 확인
        mock_tg.assert_called_once()
        mock_email.assert_called_once()
        # goal_reached_notified 플래그가 True로 변경됐는지 확인
        assert goal.goal_reached_notified is True

    @pytest.mark.asyncio
    async def test_T010_already_notified_does_not_resend(self) -> None:
        """T-010 멱등성: goal_reached_notified=True → 재발송 없음."""
        from stock_picker.scheduler.jobs import check_portfolio_goals

        goal = _make_goal(
            id=1,
            portfolio_id=10,
            target_amount=5_000_000.0,
            goal_reached_notified=True,  # 이미 발송됨
        )

        mock_session = MagicMock()
        scalars_result = MagicMock()
        scalars_result.all.return_value = [goal]
        execute_result = MagicMock()
        execute_result.scalars.return_value = scalars_result
        mock_session.execute = AsyncMock(return_value=execute_result)
        mock_session.commit = AsyncMock()

        mock_async_session_cls = MagicMock()
        mock_async_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_async_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("stock_picker.scheduler.jobs.AsyncSessionLocal", mock_async_session_cls),
            patch(
                "stock_picker.scheduler.jobs.calculate_performance",
                new=AsyncMock(return_value={"total_current": 6_000_000.0, "total_return_pct": 25.0}),
            ),
            patch("stock_picker.scheduler.jobs._send_message_sync") as mock_tg,
            patch("stock_picker.scheduler.jobs.send_general_alert_email") as mock_email,
            patch("stock_picker.scheduler.jobs.get_user_for_portfolio", return_value=MagicMock(
                id=1, email="test@example.com", username="tester"
            )),
            patch("stock_picker.scheduler.jobs.get_user_telegram_chat_id", return_value="chat123"),
        ):
            await check_portfolio_goals()

        # 이미 notified=True이므로 발송 안 함
        mock_tg.assert_not_called()
        mock_email.assert_not_called()
