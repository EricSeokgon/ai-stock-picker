# 스크리너 서비스 유닛 테스트 — TDD RED 단계
# REQ-SCR-001~007, REQ-SCR-PRESET-001~006
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stock_picker.screener.schemas import FilterRange, ScreenerCriteria, ScreenerResult
from stock_picker.screener import service as screener_service


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────


def _make_fundamental(
    krx_code: str = "005930",
    name: str = "삼성전자",
    sector: str = "전기전자",
    current_price: float | None = 71000.0,
    change_pct: float | None = -0.84,
    per: float | None = 9.2,
    pbr: float | None = 1.1,
    roe: float | None = 12.5,
    market_cap: int | None = 423_000_000_000_000,
    dividend_yield: float | None = 3.1,
    week52_high: float | None = 80000.0,
    week52_low: float | None = 60000.0,
    price_vs_52w_pct: float | None = 55.0,
    snapshot_date: date | None = None,
) -> MagicMock:
    """테스트용 StockFundamental 행 객체 생성"""
    row = MagicMock()
    row.krx_code = krx_code
    row.name = name
    row.sector = sector
    row.current_price = current_price
    row.change_pct = change_pct
    row.per = per
    row.pbr = pbr
    row.roe = roe
    row.market_cap = market_cap
    row.dividend_yield = dividend_yield
    row.week52_high = week52_high
    row.week52_low = week52_low
    row.price_vs_52w_pct = price_vs_52w_pct
    row.snapshot_date = snapshot_date or date(2026, 6, 12)
    return row


# ── FilterRange 검증 ──────────────────────────────────────────────────────────


class TestFilterRange:
    """FilterRange Pydantic 스키마 검증 (REQ-SCR-006)"""

    def test_min_only(self):
        """최솟값만 설정 가능"""
        f = FilterRange(min=1.0)
        assert f.min == 1.0
        assert f.max is None

    def test_max_only(self):
        """최댓값만 설정 가능"""
        f = FilterRange(max=10.0)
        assert f.min is None
        assert f.max == 10.0

    def test_both_valid(self):
        """min <= max 유효"""
        f = FilterRange(min=1.0, max=10.0)
        assert f.min == 1.0
        assert f.max == 10.0

    def test_min_greater_than_max_raises(self):
        """min > max이면 ValueError (REQ-SCR-006)"""
        with pytest.raises(ValueError, match="min.*max"):
            FilterRange(min=10.0, max=1.0)


# ── apply_filter 로직 테스트 ──────────────────────────────────────────────────


class TestApplyFilter:
    """스크리너 필터 적용 로직 (REQ-SCR-001~003)"""

    def test_no_filter_passes_all(self):
        """필터 없으면 모든 종목 통과 (REQ-SCR-005)"""
        rows = [_make_fundamental("005930"), _make_fundamental("000660")]
        criteria = ScreenerCriteria()
        result = screener_service.apply_filters(rows, criteria)
        assert len(result) == 2

    def test_per_max_filter(self):
        """PER 최댓값 필터 — PER 초과 종목 제외"""
        low_per = _make_fundamental("005930", per=9.0)
        high_per = _make_fundamental("000660", per=25.0)
        criteria = ScreenerCriteria(per=FilterRange(max=10.0))
        result = screener_service.apply_filters([low_per, high_per], criteria)
        assert len(result) == 1
        assert result[0].krx_code == "005930"

    def test_per_min_filter(self):
        """PER 최솟값 필터"""
        low_per = _make_fundamental("005930", per=3.0)
        high_per = _make_fundamental("000660", per=15.0)
        criteria = ScreenerCriteria(per=FilterRange(min=10.0))
        result = screener_service.apply_filters([low_per, high_per], criteria)
        assert len(result) == 1
        assert result[0].krx_code == "000660"

    def test_null_value_excluded_when_filter_active(self):
        """필터 조건 활성화 시 NULL 값 종목 제외 (REQ-SCR-003)"""
        no_per = _make_fundamental("005930", per=None)
        has_per = _make_fundamental("000660", per=5.0)
        criteria = ScreenerCriteria(per=FilterRange(max=10.0))
        result = screener_service.apply_filters([no_per, has_per], criteria)
        assert len(result) == 1
        assert result[0].krx_code == "000660"

    def test_null_value_included_when_no_filter(self):
        """필터 조건 없으면 NULL 값 종목도 포함 (REQ-SCR-005)"""
        no_per = _make_fundamental("005930", per=None)
        criteria = ScreenerCriteria()
        result = screener_service.apply_filters([no_per], criteria)
        assert len(result) == 1

    def test_and_logic_all_conditions_must_pass(self):
        """AND 조건 — 모든 필터를 만족해야 포함 (REQ-SCR-001)"""
        stock = _make_fundamental("005930", per=9.0, pbr=0.9, dividend_yield=3.5)
        # PER OK, PBR OK, 배당수익률 NG
        criteria = ScreenerCriteria(
            per=FilterRange(max=10.0),
            pbr=FilterRange(max=1.0),
            dividend_yield=FilterRange(min=4.0),
        )
        result = screener_service.apply_filters([stock], criteria)
        assert len(result) == 0

    def test_multiple_filters_all_pass(self):
        """모든 필터 통과 시 포함"""
        stock = _make_fundamental("005930", per=9.0, pbr=0.9, dividend_yield=5.0)
        criteria = ScreenerCriteria(
            per=FilterRange(max=10.0),
            pbr=FilterRange(max=1.0),
            dividend_yield=FilterRange(min=4.0),
        )
        result = screener_service.apply_filters([stock], criteria)
        assert len(result) == 1

    def test_market_cap_filter(self):
        """시가총액 필터 (단위: 원)"""
        big = _make_fundamental("005930", market_cap=400_000_000_000_000)
        small = _make_fundamental("000660", market_cap=10_000_000_000_000)
        criteria = ScreenerCriteria(market_cap=FilterRange(min=100_000_000_000_000))
        result = screener_service.apply_filters([big, small], criteria)
        assert len(result) == 1
        assert result[0].krx_code == "005930"

    def test_week52_position_filter(self):
        """52주 레인지 내 위치 필터 (price_vs_52w_pct)"""
        near_low = _make_fundamental("005930", price_vs_52w_pct=10.0)
        near_high = _make_fundamental("000660", price_vs_52w_pct=90.0)
        # 낮은 위치 (가치 저평가 필터)
        criteria = ScreenerCriteria(week52_position=FilterRange(max=30.0))
        result = screener_service.apply_filters([near_low, near_high], criteria)
        assert len(result) == 1
        assert result[0].krx_code == "005930"

    def test_roe_filter(self):
        """ROE 최솟값 필터"""
        low_roe = _make_fundamental("005930", roe=3.0)
        high_roe = _make_fundamental("000660", roe=20.0)
        criteria = ScreenerCriteria(roe=FilterRange(min=10.0))
        result = screener_service.apply_filters([low_roe, high_roe], criteria)
        assert len(result) == 1
        assert result[0].krx_code == "000660"


# ── to_screener_result 변환 테스트 ────────────────────────────────────────────


class TestToScreenerResult:
    """DB 행 → ScreenerResult 변환"""

    def test_basic_conversion(self):
        """기본 필드 변환"""
        row = _make_fundamental()
        result = screener_service.to_screener_result(row)
        assert isinstance(result, ScreenerResult)
        assert result.krx_code == "005930"
        assert result.name == "삼성전자"
        assert result.per == 9.2
        assert result.in_watchlist is False
        assert result.in_recommendations is False

    def test_in_watchlist_flag(self):
        """in_watchlist 플래그 설정"""
        row = _make_fundamental("005930")
        result = screener_service.to_screener_result(
            row, watchlist_codes={"005930", "000660"}
        )
        assert result.in_watchlist is True

    def test_in_recommendations_flag(self):
        """in_recommendations 플래그 설정"""
        row = _make_fundamental("005930")
        result = screener_service.to_screener_result(
            row, recommendation_codes={"005930"}
        )
        assert result.in_recommendations is True


# ── 프리셋 CRUD 테스트 ────────────────────────────────────────────────────────


class TestScreenerPresetService:
    """스크리너 프리셋 CRUD (REQ-SCR-PRESET-001~006)"""

    def test_list_presets_returns_user_presets(self):
        """사용자 프리셋 목록 조회 (REQ-SCR-PRESET-003)"""
        db = MagicMock()
        from stock_picker.db.models import ScreenerPreset

        p1 = MagicMock(spec=ScreenerPreset)
        p1.id = 1
        p1.user_id = 1
        p1.name = "가치투자 필터"
        p1.criteria = '{"per": {"max": 10}}'

        db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [p1]

        result = screener_service.list_presets(user_id=1, db=db)
        assert len(result) == 1
        assert result[0].name == "가치투자 필터"

    def test_create_preset_within_limit(self):
        """프리셋 생성 성공 (5개 미만)"""
        db = MagicMock()
        db.query.return_value.filter.return_value.count.return_value = 3

        from stock_picker.screener.schemas import ScreenerPresetCreate
        req = ScreenerPresetCreate(name="배당 필터", criteria=ScreenerCriteria())
        screener_service.create_preset(user_id=1, req=req, db=db)

        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_create_preset_exceeds_limit_raises_409(self):
        """5개 초과 시 HTTPException 409 (REQ-SCR-PRESET-002)"""
        from fastapi import HTTPException

        db = MagicMock()
        db.query.return_value.filter.return_value.count.return_value = 5

        from stock_picker.screener.schemas import ScreenerPresetCreate
        req = ScreenerPresetCreate(name="초과 필터", criteria=ScreenerCriteria())
        with pytest.raises(HTTPException) as exc_info:
            screener_service.create_preset(user_id=1, req=req, db=db)
        assert exc_info.value.status_code == 409

    def test_delete_preset_success(self):
        """프리셋 삭제 성공 (REQ-SCR-PRESET-004)"""
        from stock_picker.db.models import ScreenerPreset
        db = MagicMock()
        p = MagicMock(spec=ScreenerPreset)
        p.user_id = 1
        db.query.return_value.filter.return_value.first.return_value = p

        screener_service.delete_preset(user_id=1, preset_id=1, db=db)
        db.delete.assert_called_once_with(p)
        db.commit.assert_called_once()

    def test_delete_preset_not_owned_raises_403(self):
        """타인 프리셋 삭제 시 403 (REQ-SCR-PRESET-005)"""
        from fastapi import HTTPException
        from stock_picker.db.models import ScreenerPreset
        db = MagicMock()
        p = MagicMock(spec=ScreenerPreset)
        p.user_id = 2  # 다른 사용자
        db.query.return_value.filter.return_value.first.return_value = p

        with pytest.raises(HTTPException) as exc_info:
            screener_service.delete_preset(user_id=1, preset_id=1, db=db)
        assert exc_info.value.status_code in (403, 404)

    def test_delete_preset_not_found_raises_404(self):
        """존재하지 않는 프리셋 삭제 시 404"""
        from fastapi import HTTPException
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            screener_service.delete_preset(user_id=1, preset_id=999, db=db)
        assert exc_info.value.status_code == 404

    def test_create_preset_duplicate_name_raises_409(self):
        """동일 이름 프리셋 생성 시 409 (REQ-SCR-PRESET-006)"""
        from fastapi import HTTPException
        from sqlalchemy.exc import IntegrityError
        db = MagicMock()
        db.query.return_value.filter.return_value.count.return_value = 2
        db.commit.side_effect = IntegrityError("UNIQUE", {}, Exception())

        from stock_picker.screener.schemas import ScreenerPresetCreate
        req = ScreenerPresetCreate(name="중복 필터", criteria=ScreenerCriteria())
        with pytest.raises(HTTPException) as exc_info:
            screener_service.create_preset(user_id=1, req=req, db=db)
        assert exc_info.value.status_code == 409
