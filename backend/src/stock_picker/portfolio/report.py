# 포트폴리오 성과 리포트 서비스 (SPEC-STOCK-035)
# 순수 함수(generate_holding_report_rows, generate_csv_content)와
# DB 연동 서비스 함수(get_report_csv, get_report_summary, upsert_monthly_snapshot, list_monthly_snapshots) 제공
import csv
import io
from typing import Any

from sqlalchemy.orm import Session

from stock_picker.db.models import PortfolioMonthlySnapshot
from stock_picker.portfolio.schemas import HoldingReportRow

# @MX:NOTE: [AUTO] stdlib csv 모듈만 사용 — pandas·openpyxl 금지 (NFR-002)
# @MX:SPEC: SPEC-STOCK-035 NFR-002


# ─────────────────────────────────────────────────────────────
# 순수 함수 (테스트 가능, DB/네트워크 의존 없음)
# ─────────────────────────────────────────────────────────────


# @MX:ANCHOR: [AUTO] generate_holding_report_rows — 손익 계산 핵심 순수 함수
# @MX:REASON: [AUTO] router(report 엔드포인트), get_report_csv, get_report_summary 등 3곳 이상 호출
# @MX:SPEC: SPEC-STOCK-035 REQ-RPT-001
def generate_holding_report_rows(
    holdings: list[dict[str, Any]],
    prices: dict[str, float],
    fx_rates: dict[str, float],
    total_value: float,
) -> list[HoldingReportRow]:
    """보유 종목 딕셔너리 목록을 손익 계산 행(HoldingReportRow) 목록으로 변환한다.

    모든 금액은 KRW 기준. prices는 호출 전에 이미 KRW로 환산된 가격이어야 한다.
    avg_cost == 0이면 ZeroDivisionError 없이 pnl_pct=0.0을 반환한다.

    Args:
        holdings: 보유 종목 딕셔너리 목록 (ticker, name, quantity, avg_cost, market_type 포함)
        prices: {티커: 현재가(KRW)} 딕셔너리
        fx_rates: {통화코드: 환율} 딕셔너리 (예: {"USD": 1300.0}) — 현재는 참조용
        total_value: 포트폴리오 총 평가액 (KRW) — 비중 계산용

    Returns:
        HoldingReportRow 목록 (입력 종목 수와 동일)
    """
    rows: list[HoldingReportRow] = []

    for h in holdings:
        ticker = h["ticker"]
        name = h["name"]
        quantity = float(h["quantity"])
        avg_cost = float(h["avg_cost"])
        current_price = prices.get(ticker, avg_cost)  # 가격 없으면 평균단가 사용

        # 현재 평가액 (KRW)
        current_value = current_price * quantity

        # 손익 금액: (현재가 - 평균단가) × 수량
        pnl_amount = (current_price - avg_cost) * quantity

        # 수익률: 평균단가 0이면 ZeroDivisionError 방지
        if avg_cost == 0.0:
            pnl_pct = 0.0
        else:
            pnl_pct = (current_price / avg_cost - 1.0) * 100.0

        # 비중: 총 평가액 0이면 0%
        if total_value == 0.0:
            weight_pct = 0.0
        else:
            weight_pct = (current_value / total_value) * 100.0

        rows.append(
            HoldingReportRow(
                ticker=ticker,
                name=name,
                quantity=quantity,
                avg_cost=avg_cost,
                current_price=current_price,
                pnl_amount=pnl_amount,
                pnl_pct=round(pnl_pct, 4),
                weight_pct=round(weight_pct, 4),
            )
        )

    return rows


def generate_csv_content(rows: list[HoldingReportRow]) -> str:
    """HoldingReportRow 목록을 CSV 문자열로 직렬화한다.

    Python 표준 라이브러리(io.StringIO + csv.writer)만 사용한다.
    pandas, openpyxl 등 외부 라이브러리 사용 금지 (NFR-002).

    헤더: 종목코드, 종목명, 보유수량, 평균단가(KRW), 현재가(KRW), 손익(KRW), 수익률(%), 비중(%)

    Args:
        rows: HoldingReportRow 목록

    Returns:
        CSV 형식 문자열 (헤더 포함)
    """
    # @MX:NOTE: [AUTO] io.StringIO + csv.writer — NFR-002 준수
    output = io.StringIO()
    writer = csv.writer(output)

    # 헤더 8개 컬럼
    writer.writerow([
        "종목코드",
        "종목명",
        "보유수량",
        "평균단가(KRW)",
        "현재가(KRW)",
        "손익(KRW)",
        "수익률(%)",
        "비중(%)",
    ])

    for row in rows:
        writer.writerow([
            row.ticker,
            row.name,
            row.quantity,
            row.avg_cost,
            row.current_price,
            row.pnl_amount,
            row.pnl_pct,
            row.weight_pct,
        ])

    return output.getvalue()


# ─────────────────────────────────────────────────────────────
# DB 연동 서비스 함수
# ─────────────────────────────────────────────────────────────


# @MX:WARN: [AUTO] upsert_monthly_snapshot — SELECT-then-write upsert (DB-중립)
# @MX:REASON: [AUTO] ON CONFLICT 절은 SQLite와 호환되지 않아 SELECT-then-write 패턴 사용 필수
# @MX:SPEC: SPEC-STOCK-035 REQ-RPT-004
def upsert_monthly_snapshot(
    db: Session,
    portfolio_id: int,
    month: str,
    total_value_krw: float,
    total_return_pct: float | None,
    holding_count: int,
) -> PortfolioMonthlySnapshot:
    """월별 스냅샷을 DB에 upsert한다 (SELECT-then-write, DB-중립 패턴).

    ON CONFLICT 절을 사용하지 않아 SQLite와 PostgreSQL 모두 호환된다.
    동일 (portfolio_id, month)가 존재하면 기존 레코드를 업데이트하고,
    없으면 새 레코드를 INSERT한다.

    Args:
        db: SQLAlchemy 세션
        portfolio_id: 포트폴리오 ID
        month: "YYYY-MM" 형식 월 문자열
        total_value_krw: 총 평가액 (KRW)
        total_return_pct: 기간 수익률 (%), 비교 불가 시 None
        holding_count: 보유 종목 수

    Returns:
        upsert된 PortfolioMonthlySnapshot ORM 인스턴스
    """
    # 기존 레코드 조회 (SELECT-then-write)
    existing = (
        db.query(PortfolioMonthlySnapshot)
        .filter(
            PortfolioMonthlySnapshot.portfolio_id == portfolio_id,
            PortfolioMonthlySnapshot.month == month,
        )
        .first()
    )

    if existing is not None:
        # 기존 레코드 업데이트 (INSERT 없이)
        existing.total_value_krw = total_value_krw
        existing.total_return_pct = total_return_pct
        existing.holding_count = holding_count
        db.commit()
        db.refresh(existing)
        return existing

    # 새 레코드 INSERT
    snapshot = PortfolioMonthlySnapshot(
        portfolio_id=portfolio_id,
        month=month,
        total_value_krw=total_value_krw,
        total_return_pct=total_return_pct,
        holding_count=holding_count,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def list_monthly_snapshots(
    db: Session,
    portfolio_id: int,
    limit: int = 24,
) -> list[PortfolioMonthlySnapshot]:
    """포트폴리오의 월별 스냅샷 목록을 최신순으로 반환한다.

    Args:
        db: SQLAlchemy 세션
        portfolio_id: 포트폴리오 ID
        limit: 최대 반환 개수 (기본 24개 = 2년치)

    Returns:
        PortfolioMonthlySnapshot 목록 (최신 월 우선 정렬)
    """
    return (
        db.query(PortfolioMonthlySnapshot)
        .filter(PortfolioMonthlySnapshot.portfolio_id == portfolio_id)
        .order_by(PortfolioMonthlySnapshot.month.desc())
        .limit(limit)
        .all()
    )


async def get_report_service(
    db: Session,
    portfolio_id: int,
    user_id: int,
    period: str,
    redis: Any,
) -> tuple[list[HoldingReportRow], dict[str, Any]]:
    """포트폴리오 보고서 데이터 집계 서비스 함수.

    portfolio.service의 get_portfolio_with_holdings와 calculate_performance를 재사용하여
    보유 종목 손익 행 목록과 성과 요약 딕셔너리를 반환한다.

    Args:
        db: SQLAlchemy 세션
        portfolio_id: 포트폴리오 ID
        user_id: 인증된 사용자 ID (소유권 확인용)
        period: 기간 코드 ("YTD", "1M", "3M")
        redis: Redis 클라이언트

    Returns:
        (HoldingReportRow 목록, 성과 요약 딕셔너리) 튜플

    Raises:
        ValueError: 포트폴리오가 없거나 소유자가 아닌 경우
    """
    from stock_picker.portfolio.service import (
        calculate_performance,
        get_portfolio_with_holdings,
    )

    portfolio = get_portfolio_with_holdings(db, portfolio_id, user_id)
    if portfolio is None:
        raise ValueError("portfolio_not_found")

    # 성과 계산 (기존 서비스 재사용)
    perf = await calculate_performance(db, portfolio_id, user_id, redis)

    # 보유 종목에서 가격 및 손익 데이터 추출
    holdings_data: list[dict[str, Any]] = []
    prices: dict[str, float] = {}

    for h in portfolio.holdings:
        holdings_data.append({
            "ticker": h.ticker,
            "name": h.name if hasattr(h, "name") and h.name else h.ticker,
            "quantity": h.quantity,
            "avg_cost": h.avg_cost,
            "market_type": h.market_type if hasattr(h, "market_type") else "KRX",
        })
        # current_price는 성과 계산 결과에서 추출 (없으면 avg_cost 사용)
        current_price = h.avg_cost
        if perf and "holdings" in perf:
            for ph in perf.get("holdings", []):
                if ph.get("ticker") == h.ticker:
                    current_price = ph.get("current_price", h.avg_cost)
                    break
        prices[h.ticker] = current_price

    # 총 평가액 계산
    total_value = sum(
        prices.get(h["ticker"], h["avg_cost"]) * h["quantity"]
        for h in holdings_data
    )

    rows = generate_holding_report_rows(holdings_data, prices, {}, total_value)
    return rows, perf or {}
