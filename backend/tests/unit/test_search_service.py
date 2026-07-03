# 종목 검색 서비스 단위 테스트 (SPEC-STOCK-007 TASK-008)
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


# 테스트용 CSV 픽스처 경로
_FIXTURE_CSV = (
    Path(__file__).parent.parent / "fixtures" / "krx_master.csv"
)


def _make_db(recent_codes: set[str] | None = None):
    """mock AsyncSession 생성. recent_codes가 None이면 빈 집합 반환."""
    db = AsyncMock()
    codes = recent_codes or set()

    # result.all()은 동기 메서드
    mock_result = MagicMock()
    mock_result.all = MagicMock(return_value=[(code,) for code in codes])
    db.execute.return_value = mock_result
    return db


class TestSearchStocks:
    """search_stocks 함수 단위 테스트"""

    @pytest.mark.asyncio
    async def test_partial_name_match_returns_results(self):
        """종목명 부분 일치 검색 — '삼성' 검색 시 삼성전자 포함"""
        from stock_picker.search.service import search_stocks

        db = _make_db()
        results = await search_stocks(q="삼성", db=db, csv_path=_FIXTURE_CSV)

        codes = [r["krx_code"] for r in results]
        assert "005930" in codes  # 삼성전자

    @pytest.mark.asyncio
    async def test_code_prefix_match_returns_results(self):
        """KRX 코드 접두어 검색 — '00593' 검색 시 005930 포함"""
        from stock_picker.search.service import search_stocks

        db = _make_db()
        results = await search_stocks(q="00593", db=db, csv_path=_FIXTURE_CSV)

        assert any(r["krx_code"] == "005930" for r in results)

    @pytest.mark.asyncio
    async def test_in_recommendations_true_when_in_recent(self):
        """최근 추천 종목은 in_recommendations=True"""
        from stock_picker.search.service import search_stocks

        db = _make_db(recent_codes={"005930"})
        results = await search_stocks(q="삼성전자", db=db, csv_path=_FIXTURE_CSV)

        samsung = next((r for r in results if r["krx_code"] == "005930"), None)
        assert samsung is not None
        assert samsung["in_recommendations"] is True

    @pytest.mark.asyncio
    async def test_in_recommendations_false_when_not_in_recent(self):
        """추천되지 않은 종목은 in_recommendations=False"""
        from stock_picker.search.service import search_stocks

        db = _make_db(recent_codes=set())
        results = await search_stocks(q="삼성전자", db=db, csv_path=_FIXTURE_CSV)

        samsung = next((r for r in results if r["krx_code"] == "005930"), None)
        assert samsung is not None
        assert samsung["in_recommendations"] is False

    @pytest.mark.asyncio
    async def test_results_limited_to_max(self):
        """결과는 max_results를 초과하지 않음"""
        from stock_picker.search.service import search_stocks

        db = _make_db()
        # 매우 짧은 쿼리로 많은 결과 유도
        results = await search_stocks(q="0", db=db, max_results=3, csv_path=_FIXTURE_CSV)

        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty_list(self):
        """빈 쿼리는 빈 리스트 반환"""
        from stock_picker.search.service import search_stocks

        db = _make_db()
        results = await search_stocks(q="", db=db, csv_path=_FIXTURE_CSV)

        assert results == []

    @pytest.mark.asyncio
    async def test_recommended_stocks_sorted_first(self):
        """in_recommendations=True인 종목이 결과 앞쪽에 위치"""
        from stock_picker.search.service import search_stocks

        # SK하이닉스(000660)만 추천 종목으로 설정
        db = _make_db(recent_codes={"000660"})
        results = await search_stocks(q="0", db=db, csv_path=_FIXTURE_CSV)

        if len(results) >= 2:
            recommended = [r for r in results if r["in_recommendations"]]
            not_recommended = [r for r in results if not r["in_recommendations"]]

            if recommended and not_recommended:
                first_not_recommended_idx = results.index(not_recommended[0])
                last_recommended_idx = results.index(recommended[-1])
                assert last_recommended_idx < first_not_recommended_idx

    @pytest.mark.asyncio
    async def test_no_match_returns_empty_list(self):
        """매칭 없으면 빈 리스트 반환"""
        from stock_picker.search.service import search_stocks

        db = _make_db()
        results = await search_stocks(q="ZZZZNOTEXIST999", db=db, csv_path=_FIXTURE_CSV)

        assert results == []

    @pytest.mark.asyncio
    async def test_db_failure_returns_empty_recommendations_gracefully(self):
        """DB 조회 실패 시에도 검색 결과는 반환 (in_recommendations=False)"""
        from stock_picker.search.service import search_stocks

        db = AsyncMock()
        db.execute.side_effect = Exception("DB 연결 오류")

        results = await search_stocks(q="삼성전자", db=db, csv_path=_FIXTURE_CSV)

        # 검색 자체는 성공, in_recommendations은 모두 False
        assert isinstance(results, list)
        for r in results:
            assert r["in_recommendations"] is False
