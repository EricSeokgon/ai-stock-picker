# 피드백 서비스 단위 테스트 (SPEC-STOCK-007 TASK-010)
from unittest.mock import AsyncMock, MagicMock

import pytest

from stock_picker.db.models import RecommendationFeedback


def _make_db(vote_counts: dict | None = None):
    """mock AsyncSession 생성.

    vote_counts: {"up": N, "down": M} 형태로 집계 결과 설정
    """
    db = AsyncMock()

    if vote_counts is not None:
        # get_feedback_summary용 mock 결과
        rows = []
        for vote, cnt in vote_counts.items():
            row = MagicMock()
            row.vote = vote
            row.cnt = cnt
            rows.append(row)

        # result.all()은 동기 메서드여야 함
        mock_result = MagicMock()
        mock_result.all = MagicMock(return_value=rows)
        db.execute.return_value = mock_result

    return db


class TestSaveFeedback:
    """save_feedback 함수 단위 테스트"""

    @pytest.mark.asyncio
    async def test_save_up_vote(self):
        """up 투표 저장 — commit/refresh 호출 확인"""
        from stock_picker.feedback.service import save_feedback

        db = AsyncMock()
        result = await save_feedback(db=db, krx_code="005930", vote="up")

        db.add.assert_called_once()
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()
        assert isinstance(result, RecommendationFeedback)
        assert result.vote == "up"
        assert result.krx_code == "005930"

    @pytest.mark.asyncio
    async def test_save_down_vote(self):
        """down 투표 저장 — commit/refresh 호출 확인"""
        from stock_picker.feedback.service import save_feedback

        db = AsyncMock()
        result = await save_feedback(db=db, krx_code="005930", vote="down")

        db.add.assert_called_once()
        db.commit.assert_awaited_once()
        assert isinstance(result, RecommendationFeedback)
        assert result.vote == "down"
        assert result.krx_code == "005930"

    @pytest.mark.asyncio
    async def test_invalid_vote_raises_value_error(self):
        """유효하지 않은 vote 값 → ValueError 발생"""
        from stock_picker.feedback.service import save_feedback

        db = AsyncMock()
        with pytest.raises(ValueError, match="유효하지 않습니다"):
            await save_feedback(db=db, krx_code="005930", vote="maybe")

    @pytest.mark.asyncio
    async def test_anonymous_user_accepted(self):
        """user_id=None (비로그인) 투표 허용"""
        from stock_picker.feedback.service import save_feedback

        db = AsyncMock()
        await save_feedback(db=db, krx_code="005930", vote="up", user_id=None)

        # add 호출 인자에서 user_id 확인
        added_obj: RecommendationFeedback = db.add.call_args[0][0]
        assert added_obj.user_id is None

    @pytest.mark.asyncio
    async def test_with_user_id_sets_correctly(self):
        """user_id 있는 경우 모델에 설정"""
        from stock_picker.feedback.service import save_feedback

        db = AsyncMock()
        await save_feedback(db=db, krx_code="005930", vote="down", user_id=42)

        added_obj: RecommendationFeedback = db.add.call_args[0][0]
        assert added_obj.user_id == 42

    @pytest.mark.asyncio
    async def test_empty_vote_raises_value_error(self):
        """빈 vote 문자열 → ValueError 발생"""
        from stock_picker.feedback.service import save_feedback

        db = AsyncMock()
        with pytest.raises(ValueError):
            await save_feedback(db=db, krx_code="005930", vote="")


class TestGetFeedbackSummary:
    """get_feedback_summary 함수 단위 테스트"""

    @pytest.mark.asyncio
    async def test_returns_correct_counts(self):
        """up/down 카운트 정확히 반환"""
        from stock_picker.feedback.service import get_feedback_summary

        db = _make_db(vote_counts={"up": 5, "down": 3})
        result = await get_feedback_summary(db=db, krx_code="005930")

        assert result["krx_code"] == "005930"
        assert result["up"] == 5
        assert result["down"] == 3

    @pytest.mark.asyncio
    async def test_no_votes_returns_zeros(self):
        """투표 없으면 up=0, down=0"""
        from stock_picker.feedback.service import get_feedback_summary

        db = _make_db(vote_counts={})
        result = await get_feedback_summary(db=db, krx_code="000660")

        assert result["up"] == 0
        assert result["down"] == 0

    @pytest.mark.asyncio
    async def test_only_up_votes(self):
        """up 투표만 있는 경우"""
        from stock_picker.feedback.service import get_feedback_summary

        db = _make_db(vote_counts={"up": 10})
        result = await get_feedback_summary(db=db, krx_code="005930")

        assert result["up"] == 10
        assert result["down"] == 0
