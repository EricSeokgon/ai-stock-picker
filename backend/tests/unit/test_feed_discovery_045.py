# SPEC-STOCK-045: 피드 디스커버리 강화 단위 테스트
# 실행: cd backend && .venv/bin/pytest tests/unit/test_feed_discovery_045.py -v
"""
T-045-001: 트렌딩: 7일 합계 큰 항목이 먼저  (REQ-FEED-002 / AC-001)
T-045-002: 트렌딩: 상위 합계가 앞 인덱스     (REQ-FEED-002 / AC-002)
T-045-003: 트렌딩: 조회 0 항목은 양수 뒤     (REQ-FEED-003 / AC-003)
T-045-004: 검색: 이름 부분 일치만 반환        (REQ-FEED-004 / AC-004)
T-045-005: 검색: 대소문자 무시 매칭           (REQ-FEED-004 / AC-005)
T-045-006: 빈 q → 무필터 전체 반환           (REQ-FEED-005 / AC-006)
T-045-007: 알 수 없는 sort → recent 폴백      (REQ-FEED-006 / AC-007)
T-045-008: total = q 필터 후 개수             (REQ-FEED-007 / AC-008)
"""
from __future__ import annotations

from unittest.mock import MagicMock


# ─────────────────────────────────────────────────────────────────────────────
# 헬퍼: mock 행(row) 및 mock DB 생성
# ─────────────────────────────────────────────────────────────────────────────

def _make_row(
    share_token: str,
    portfolio_name: str,
    view_count: int = 0,
    like_count: int | None = None,
    share_id: int = 1,
) -> tuple:
    """피드 쿼리 한 행 (share, portfolio, like_cnt) 모의 객체."""
    from stock_picker.db.models import Portfolio, PortfolioShare

    share = MagicMock(spec=PortfolioShare)
    share.id = share_id
    share.share_token = share_token
    share.share_url = f"/shared/{share_token}"
    share.portfolio_id = share_id
    share.view_count = view_count

    portfolio = MagicMock(spec=Portfolio)
    portfolio.id = share_id
    portfolio.name = portfolio_name

    return (share, portfolio, like_count)


def _build_mock_db(rows: list, total: int, n_query_calls: int = 2):
    """
    n_query_calls 개의 db.query() 호출을 처리하는 mock Session 생성.

    - non-trending: 2 calls (like_count_subq, base_query)
    - trending:     3 calls (like_count_subq, trending_subq, base_query)

    마지막 call 이 base_query — count/rows 를 반환.
    """
    db = MagicMock()

    def _chain(count_val: int = 0, rows_val: list | None = None) -> MagicMock:
        """자기 자신을 반환하는 체인 가능한 mock."""
        m = MagicMock()
        for method in ("group_by", "filter", "join", "outerjoin", "order_by", "offset", "limit"):
            getattr(m, method).return_value = m
        m.subquery.return_value = MagicMock(name="subq")
        m.count.return_value = count_val
        m.all.return_value = rows_val if rows_val is not None else []
        return m

    # db.query 호출 순서: [0] like_count_subq, [1] base_query, [2] trending_subq (있을 경우)
    # base_query 는 항상 인덱스 1 (두 번째 호출) — total/rows 를 여기에 배치
    chains = [_chain() for _ in range(n_query_calls)]
    chains[1] = _chain(total, rows)  # base_query mock
    db.query.side_effect = chains
    return db


# ─────────────────────────────────────────────────────────────────────────────
# T-045-001 ~ T-045-003: 트렌딩 정렬
# ─────────────────────────────────────────────────────────────────────────────

class TestTrendingSort:
    """sort=trending 동작 검증 (REQ-FEED-002, REQ-FEED-003)"""

    def test_t045_001_higher_view_sum_appears_first(self) -> None:
        """T-045-001: 7일 합계 큰 항목이 먼저 반환됨."""
        from stock_picker.portfolio.sharing import get_feed

        rows = [
            _make_row("tok_high", "고조회 포트폴리오", view_count=50, share_id=1),
            _make_row("tok_low", "저조회 포트폴리오", view_count=10, share_id=2),
        ]
        db = _build_mock_db(rows, total=2, n_query_calls=3)  # trending → 3 queries

        result = get_feed(db, sort="trending")

        assert result["items"][0]["share_token"] == "tok_high"
        assert result["items"][1]["share_token"] == "tok_low"

    def test_t045_002_higher_sum_at_earlier_index(self) -> None:
        """T-045-002: 합계 큰 항목이 낮은 인덱스에 위치."""
        from stock_picker.portfolio.sharing import get_feed

        rows = [
            _make_row("tok_a", "A 포트폴리오", view_count=100, share_id=1),
            _make_row("tok_b", "B 포트폴리오", view_count=30, share_id=2),
            _make_row("tok_c", "C 포트폴리오", view_count=5, share_id=3),
        ]
        db = _build_mock_db(rows, total=3, n_query_calls=3)

        result = get_feed(db, sort="trending")

        assert result["items"][0]["share_token"] == "tok_a"
        assert result["items"][1]["share_token"] == "tok_b"
        assert result["items"][2]["share_token"] == "tok_c"

    def test_t045_003_zero_view_appears_after_positive(self) -> None:
        """T-045-003: 최근 조회 0 항목은 양수 항목 뒤에 위치."""
        from stock_picker.portfolio.sharing import get_feed

        rows = [
            _make_row("tok_viewed", "조회된 포트폴리오", view_count=20, share_id=1),
            _make_row("tok_zero", "조회 없는 포트폴리오", view_count=0, share_id=2),
        ]
        db = _build_mock_db(rows, total=2, n_query_calls=3)

        result = get_feed(db, sort="trending")

        assert result["items"][0]["share_token"] == "tok_viewed"
        assert result["items"][1]["share_token"] == "tok_zero"

    def test_t045_trending_makes_three_db_query_calls(self) -> None:
        """sort=trending 시 db.query 가 3번 호출되어야 함 (trending_subq 추가)."""
        from stock_picker.portfolio.sharing import get_feed

        db = _build_mock_db([], total=0, n_query_calls=3)

        get_feed(db, sort="trending")

        assert db.query.call_count == 3


# ─────────────────────────────────────────────────────────────────────────────
# T-045-004 ~ T-045-006, T-045-008: 검색 필터
# ─────────────────────────────────────────────────────────────────────────────

class TestSearchFilter:
    """q 파라미터 이름 검색 동작 검증 (REQ-FEED-004, REQ-FEED-005, REQ-FEED-007)"""

    def test_t045_004_q_partial_match_returns_matching(self) -> None:
        """T-045-004: q='성장' → '성장' 포함 항목만 반환."""
        from stock_picker.portfolio.sharing import get_feed

        rows = [_make_row("tok_growth", "성장 포트폴리오")]
        db = _build_mock_db(rows, total=1, n_query_calls=2)

        result = get_feed(db, q="성장")

        assert len(result["items"]) == 1
        assert result["items"][0]["portfolio_name"] == "성장 포트폴리오"

    def test_t045_005_q_case_insensitive(self) -> None:
        """T-045-005: q='etf' → 'Dividend ETF' 포함."""
        from stock_picker.portfolio.sharing import get_feed

        rows = [_make_row("tok_etf", "Dividend ETF")]
        db = _build_mock_db(rows, total=1, n_query_calls=2)

        result = get_feed(db, q="etf")

        assert len(result["items"]) == 1
        assert result["items"][0]["portfolio_name"] == "Dividend ETF"

    def test_t045_006_empty_q_returns_all(self) -> None:
        """T-045-006: q='' → 필터 없이 전체 반환."""
        from stock_picker.portfolio.sharing import get_feed

        rows = [
            _make_row("tok_1", "포트폴리오 1", share_id=1),
            _make_row("tok_2", "포트폴리오 2", share_id=2),
        ]
        db = _build_mock_db(rows, total=2, n_query_calls=2)

        result = get_feed(db, q="")

        assert result["total"] == 2
        assert len(result["items"]) == 2

    def test_t045_008_total_equals_filtered_count(self) -> None:
        """T-045-008: q 필터 후 total = 매칭 개수."""
        from stock_picker.portfolio.sharing import get_feed

        rows = [
            _make_row("tok_1", "배당 포트폴리오 1", share_id=1),
            _make_row("tok_2", "배당 포트폴리오 2", share_id=2),
            _make_row("tok_3", "배당 포트폴리오 3", share_id=3),
        ]
        db = _build_mock_db(rows, total=3, n_query_calls=2)  # 10개 중 3개 매칭

        result = get_feed(db, q="배당")

        assert result["total"] == 3


# ─────────────────────────────────────────────────────────────────────────────
# T-045-007: 알 수 없는 sort 폴백
# ─────────────────────────────────────────────────────────────────────────────

class TestUnknownSortFallback:
    """REQ-FEED-006: 미지원 sort → recent 폴백, 에러 없음"""

    def test_t045_007_unknown_sort_no_error(self) -> None:
        """T-045-007: sort='popular' → 예외 없이 200 응답."""
        from stock_picker.portfolio.sharing import get_feed

        rows = [_make_row("tok_1", "포트폴리오 1")]
        db = _build_mock_db(rows, total=1, n_query_calls=2)

        result = get_feed(db, sort="popular")  # 미지원 값

        assert result is not None
        assert "items" in result
        assert result["total"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# T-045-008 추가: trending + pagination 조합
# ─────────────────────────────────────────────────────────────────────────────

class TestTrendingPagination:
    """트렌딩 정렬 + 페이지네이션 조합"""

    def test_t045_trending_pagination_structure(self) -> None:
        """trending + page=2, size=2 → 올바른 page/size/total 반환."""
        from stock_picker.portfolio.sharing import get_feed

        rows = [_make_row("tok_3", "포트폴리오 3", share_id=3)]
        db = _build_mock_db(rows, total=5, n_query_calls=3)

        result = get_feed(db, sort="trending", page=2, size=2)

        assert result["page"] == 2
        assert result["size"] == 2
        assert result["total"] == 5
        assert len(result["items"]) == 1
