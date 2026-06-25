"""SPEC-STOCK-039 — KRX 장중 판정 순수 함수 및 시장 상태 엔드포인트 단위 테스트.

RED 단계: 모든 테스트가 처음에 실패해야 한다.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

# 테스트 대상 임포트 (아직 존재하지 않음 — RED 상태)
from stock_picker.portfolio.market_status import is_krx_open

# 한국 시간대 상수
KST = ZoneInfo("Asia/Seoul")


# ── TestIsKrxOpen: 순수 함수 단위 테스트 (10개) ──────────────────────────────


class TestIsKrxOpen:
    """is_krx_open 순수 함수 경계 조건 및 요일 검증."""

    def test_평일_10시_장중_반환(self) -> None:
        """평일 10:00 KST → True."""
        # 월요일 10:00 KST
        dt = datetime(2026, 6, 22, 10, 0, 0, tzinfo=KST)  # 2026-06-22 월요일
        assert is_krx_open(dt) is True

    def test_평일_09시_경계_포함_반환(self) -> None:
        """평일 09:00:00 KST (개장 경계 포함) → True."""
        dt = datetime(2026, 6, 22, 9, 0, 0, tzinfo=KST)
        assert is_krx_open(dt) is True

    def test_평일_1530_경계_포함_반환(self) -> None:
        """평일 15:30:00 KST (폐장 경계 포함) → True."""
        dt = datetime(2026, 6, 22, 15, 30, 0, tzinfo=KST)
        assert is_krx_open(dt) is True

    def test_평일_0859_장전_반환(self) -> None:
        """평일 08:59:59 KST (개장 전) → False."""
        dt = datetime(2026, 6, 22, 8, 59, 59, tzinfo=KST)
        assert is_krx_open(dt) is False

    def test_평일_1531_장후_반환(self) -> None:
        """평일 15:30:01 KST (폐장 후) → False."""
        dt = datetime(2026, 6, 22, 15, 30, 1, tzinfo=KST)
        assert is_krx_open(dt) is False

    def test_토요일_장중시간_반환(self) -> None:
        """토요일 10:00 KST → False (주말)."""
        # 2026-06-20 토요일
        dt = datetime(2026, 6, 20, 10, 0, 0, tzinfo=KST)
        assert is_krx_open(dt) is False

    def test_일요일_장중시간_반환(self) -> None:
        """일요일 10:00 KST → False (주말)."""
        # 2026-06-21 일요일
        dt = datetime(2026, 6, 21, 10, 0, 0, tzinfo=KST)
        assert is_krx_open(dt) is False

    def test_평일_자정_반환(self) -> None:
        """평일 00:00 KST → False."""
        dt = datetime(2026, 6, 22, 0, 0, 0, tzinfo=KST)
        assert is_krx_open(dt) is False

    def test_평일_2359_반환(self) -> None:
        """평일 23:59 KST → False."""
        dt = datetime(2026, 6, 22, 23, 59, 0, tzinfo=KST)
        assert is_krx_open(dt) is False

    def test_UTC_시각_입력_KST_변환_판정(self) -> None:
        """UTC 입력 시 KST로 자동 변환하여 판정.

        UTC 01:00 = KST 10:00 → True (평일 장중).
        2026-06-22(월) UTC 01:00 = KST 10:00.
        """
        UTC = ZoneInfo("UTC")
        # UTC 01:00 = KST 10:00 (평일 장중)
        dt_utc = datetime(2026, 6, 22, 1, 0, 0, tzinfo=UTC)
        # is_krx_open은 timezone-aware datetime을 받아 KST로 변환
        assert is_krx_open(dt_utc) is True


# ── TestMarketStatusEndpoint: HTTP 엔드포인트 테스트 (3개) ───────────────────


class TestMarketStatusEndpoint:
    """GET /portfolios/market-status 엔드포인트 검증."""

    @pytest.fixture()
    def client(self) -> TestClient:
        """FastAPI TestClient (인증 없이 사용).

        기존 테스트 패턴과 동일하게 mini FastAPI 앱에 router를 직접 등록한다.
        """
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from stock_picker.portfolio.router import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_200_반환_인증_없이(self, client: TestClient) -> None:
        """GET /portfolios/market-status → 200 (인증 불필요)."""
        resp = client.get("/portfolios/market-status")
        assert resp.status_code == 200

    def test_응답_body_is_open_message_필드_존재(self, client: TestClient) -> None:
        """응답 body에 is_open(bool), message(str) 필드가 있어야 한다."""
        resp = client.get("/portfolios/market-status")
        assert resp.status_code == 200
        body = resp.json()
        assert "is_open" in body
        assert isinstance(body["is_open"], bool)
        assert "message" in body
        assert isinstance(body["message"], str)

    def test_장중_메시지_및_장마감_메시지(self, client: TestClient) -> None:
        """is_krx_open 모킹으로 메시지 분기 검증.

        is_krx_open=True → message='장 중'
        is_krx_open=False → message='장 마감'
        """
        # 장 중 케이스
        with patch(
            "stock_picker.portfolio.router.is_krx_open",
            return_value=True,
        ):
            resp = client.get("/portfolios/market-status")
            assert resp.status_code == 200
            body = resp.json()
            assert body["is_open"] is True
            assert body["message"] == "장 중"

        # 장 마감 케이스
        with patch(
            "stock_picker.portfolio.router.is_krx_open",
            return_value=False,
        ):
            resp = client.get("/portfolios/market-status")
            assert resp.status_code == 200
            body = resp.json()
            assert body["is_open"] is False
            assert body["message"] == "장 마감"
