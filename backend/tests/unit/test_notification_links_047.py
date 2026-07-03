# SPEC-STOCK-047: 공유 포트폴리오 알림 딥링크 단위 테스트
# 테스트 실행: backend/.venv/bin/pytest backend/tests/unit/test_notification_links_047.py -v
"""
T-047-001 ~ T-047-009 (백엔드 9개)

커버리지 대상:
- _resolve_links: 알림 목록에서 딥링크 일괄 산출 (async, N+1 없음)
- _to_schema: link 인자 주입 지원
- NotificationSchema: link 필드 존재 확인
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# 헬퍼 팩토리
# ─────────────────────────────────────────────────────────────────────────────


def _make_mock_notification(
    noti_id: int = 1,
    ntype: str = "portfolio_like",
    krx_code: str = "P7",
    is_read: bool = False,
) -> object:
    """Notification 모의 객체 생성"""
    from stock_picker.db.models import Notification

    n = MagicMock(spec=Notification)
    n.id = noti_id
    n.type = ntype
    n.krx_code = krx_code
    n.title = "테스트 알림"
    n.body = None
    n.is_read = is_read
    n.ref_date = None
    n.related_alert_id = None
    n.created_at = datetime(2026, 7, 1, 10, 0, 0, tzinfo=timezone.utc)
    n.read_at = None
    return n


def _make_share_row(portfolio_id: int, share_token: str) -> object:
    """PortfolioShare 조회 결과 행 모의 객체"""
    row = MagicMock()
    row.portfolio_id = portfolio_id
    row.share_token = share_token
    return row


def _make_mock_db(rows: list | None = None) -> AsyncMock:
    """AsyncSession mock — execute().all() 반환값으로 rows 설정"""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = rows or []
    db.execute.return_value = mock_result
    return db


# ─────────────────────────────────────────────────────────────────────────────
# T-047-001: 댓글 알림 + 공개 공유(token abc123) → link `/shared/abc123`
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_notification_link_portfolio_comment() -> None:
    """portfolio_comment 알림 + 활성 공개 공유 → link /shared/abc123 반환 (AC-047-001)"""
    from stock_picker.notifications.inbox_router import _resolve_links

    n = _make_mock_notification(noti_id=1, ntype="portfolio_comment", krx_code="P7")
    db = _make_mock_db(rows=[_make_share_row(portfolio_id=7, share_token="abc123")])

    links = await _resolve_links(db, [n])

    assert links[1] == "/shared/abc123"


# ─────────────────────────────────────────────────────────────────────────────
# T-047-002: 좋아요 알림 + 공개 공유 → link non-null
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_notification_link_portfolio_like() -> None:
    """portfolio_like 알림 + 활성 공개 공유 → link non-null 반환 (AC-047-002)"""
    from stock_picker.notifications.inbox_router import _resolve_links

    n = _make_mock_notification(noti_id=2, ntype="portfolio_like", krx_code="P10")
    db = _make_mock_db(rows=[_make_share_row(portfolio_id=10, share_token="tok_xyz")])

    links = await _resolve_links(db, [n])

    assert links[2] is not None
    assert links[2].startswith("/shared/")


# ─────────────────────────────────────────────────────────────────────────────
# T-047-003: price_alert 알림 → link null, DB 조회 없음
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_notification_link_other_type() -> None:
    """price_alert 등 다른 타입 알림 → link null, DB 쿼리 없음 (AC-047-003)"""
    from stock_picker.notifications.inbox_router import _resolve_links

    n = _make_mock_notification(noti_id=3, ntype="price_alert", krx_code="005930")
    db = _make_mock_db()

    links = await _resolve_links(db, [n])

    assert links[3] is None
    # 포트폴리오 알림 없으면 DB 조회 불필요
    db.execute.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# T-047-004: portfolio_like + 비공개/없는 공유 → link null
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_notification_link_no_active_share() -> None:
    """portfolio_like + 활성 공개 공유 없음 → link null (AC-047-004)"""
    from stock_picker.notifications.inbox_router import _resolve_links

    n = _make_mock_notification(noti_id=4, ntype="portfolio_like", krx_code="P5")
    db = _make_mock_db(rows=[])  # 공개 공유 없음

    links = await _resolve_links(db, [n])

    assert links[4] is None


# ─────────────────────────────────────────────────────────────────────────────
# T-047-005: 규약 불일치 krx_code → link null
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_notification_link_invalid_krx_code() -> None:
    """portfolio_comment 알림이라도 krx_code가 P{id} 패턴 불일치 → link null (AC-047-005)"""
    from stock_picker.notifications.inbox_router import _resolve_links

    n = _make_mock_notification(noti_id=5, ntype="portfolio_comment", krx_code="005930")
    db = _make_mock_db()

    links = await _resolve_links(db, [n])

    assert links[5] is None


# ─────────────────────────────────────────────────────────────────────────────
# T-047-006: NotificationSchema에 link 필드 존재
# ─────────────────────────────────────────────────────────────────────────────


def test_notification_link_schema_field() -> None:
    """NotificationSchema에 link 필드가 존재하고 기본값 None (T-047-006)"""
    from stock_picker.notifications.inbox_router import NotificationSchema

    fields = NotificationSchema.model_fields
    assert "link" in fields, "NotificationSchema에 link 필드 없음"
    # 필드가 Optional(기본값 None)이어야 함
    field = fields["link"]
    assert not field.is_required(), "link 필드는 Optional이어야 합니다"


# ─────────────────────────────────────────────────────────────────────────────
# T-047-007: _to_schema가 link 인자를 받아 NotificationSchema.link에 주입
# ─────────────────────────────────────────────────────────────────────────────


def test_to_schema_with_link() -> None:
    """_to_schema(n, link=...) → NotificationSchema.link 필드에 주입 (AC-047-006)"""
    from stock_picker.notifications.inbox_router import _to_schema

    n = _make_mock_notification(noti_id=6, ntype="portfolio_comment", krx_code="P7")
    schema = _to_schema(n, link="/shared/abc123")

    assert schema.link == "/shared/abc123"


def test_to_schema_default_link_none() -> None:
    """_to_schema(n) 링크 미지정 → link=None (하위 호환)"""
    from stock_picker.notifications.inbox_router import _to_schema

    n = _make_mock_notification(noti_id=7, ntype="price_alert", krx_code="005930")
    schema = _to_schema(n)

    assert schema.link is None


# ─────────────────────────────────────────────────────────────────────────────
# T-047-008: 다중 포트폴리오 알림 단일 배치 쿼리로 각각 올바른 link
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_notification_list_batch_query() -> None:
    """서로 다른 두 포트폴리오 알림 → 단일 쿼리로 각자 올바른 link 산출 (AC-047-007)"""
    from stock_picker.notifications.inbox_router import _resolve_links

    n1 = _make_mock_notification(noti_id=10, ntype="portfolio_like", krx_code="P7")
    n2 = _make_mock_notification(noti_id=11, ntype="portfolio_comment", krx_code="P9")
    db = _make_mock_db(
        rows=[
            _make_share_row(portfolio_id=7, share_token="tok_seven"),
            _make_share_row(portfolio_id=9, share_token="tok_nine"),
        ]
    )

    links = await _resolve_links(db, [n1, n2])

    assert links[10] == "/shared/tok_seven"
    assert links[11] == "/shared/tok_nine"
    # N+1 아님: execute 1회만 호출
    assert db.execute.call_count == 1


# ─────────────────────────────────────────────────────────────────────────────
# T-047-009: 혼합 알림 목록 (포트폴리오 + 일반) 각각 올바른 link
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_notification_mixed_types() -> None:
    """포트폴리오 + 가격 알림 혼합 → 포트폴리오만 link, 일반은 null"""
    from stock_picker.notifications.inbox_router import _resolve_links

    n_like = _make_mock_notification(noti_id=20, ntype="portfolio_like", krx_code="P3")
    n_price = _make_mock_notification(noti_id=21, ntype="price_alert", krx_code="005930")
    db = _make_mock_db(rows=[_make_share_row(portfolio_id=3, share_token="tok_three")])

    links = await _resolve_links(db, [n_like, n_price])

    assert links[20] == "/shared/tok_three"
    assert links[21] is None
