# 백테스트 실행 엔진 — momentum/volume 전략
import asyncio
import logging
from datetime import date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from stock_picker.backtest.metrics import (
    calculate_cagr,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
)

logger = logging.getLogger(__name__)

# 전략별 상위 종목 수
_TOP_N = 5
# 모멘텀/볼륨 계산 기간 (거래일)
_LOOKBACK_DAYS = 20


def _get_krx_universe() -> list[str]:
    """KRX 주요 종목 코드 목록 반환 — 실제 환경에서는 더 넓은 유니버스 사용"""
    # 코스피 200 주요 종목 샘플
    return [
        "005930",  # 삼성전자
        "000660",  # SK하이닉스
        "005380",  # 현대차
        "051910",  # LG화학
        "006400",  # 삼성SDI
        "035420",  # NAVER
        "035720",  # 카카오
        "028260",  # 삼성물산
        "068270",  # 셀트리온
        "105560",  # KB금융
    ]


def _fetch_price_data(krx_codes: list[str], start_date: date, end_date: date) -> dict:
    """FinanceDataReader로 가격 데이터 조회 — 동기 함수.

    # @MX:WARN: [AUTO] 외부 API 블로킹 호출 — 스레드 풀에서 실행 필요
    # @MX:REASON: FinanceDataReader는 동기 HTTP 요청이므로 asyncio 루프를 블로킹함

    Returns:
        {krx_code: DataFrame} 형태
    """
    import FinanceDataReader as fdr

    price_data = {}
    for code in krx_codes:
        try:
            df = fdr.DataReader(code, start=str(start_date), end=str(end_date))
            if df is not None and not df.empty:
                price_data[code] = df
        except Exception:
            logger.warning("가격 데이터 조회 실패 — krx_code=%s", code)
    return price_data


def _run_momentum_strategy(
    price_data: dict, start_date: date, end_date: date
) -> list[dict]:
    """모멘텀 전략: 월별 20거래일 수익률 상위 5 종목 매수.

    Returns:
        [{"trade_date": date, "krx_code": str, "signal": str, "price": float, "return_pct": float}]
    """
    import pandas as pd

    results = []

    for code, df in price_data.items():
        if "Close" not in df.columns or len(df) < _LOOKBACK_DAYS:
            continue

        df = df.sort_index()
        # 일별 수익률 계산
        df["daily_return"] = df["Close"].pct_change()
        # 20거래일 모멘텀 스코어
        df["momentum"] = df["Close"].pct_change(periods=_LOOKBACK_DAYS)

        for idx, row in df.iterrows():
            trade_date = idx.date() if hasattr(idx, "date") else idx
            if trade_date < start_date or trade_date > end_date:
                continue
            if pd.isna(row.get("momentum", float("nan"))):
                continue

            results.append({
                "trade_date": trade_date,
                "krx_code": code,
                "signal": "buy" if row["momentum"] > 0 else "sell",
                "price": float(row["Close"]),
                "return_pct": float(row["daily_return"]) if not pd.isna(row.get("daily_return", float("nan"))) else None,
            })

    return sorted(results, key=lambda x: x["trade_date"])


def _run_volume_strategy(
    price_data: dict, start_date: date, end_date: date
) -> list[dict]:
    """볼륨 전략: 월별 20거래일 거래량 비율 상위 5 종목 매수.

    Returns:
        [{"trade_date": date, "krx_code": str, "signal": str, "price": float, "return_pct": float}]
    """
    import pandas as pd

    results = []

    for code, df in price_data.items():
        if "Close" not in df.columns or "Volume" not in df.columns:
            continue
        if len(df) < _LOOKBACK_DAYS:
            continue

        df = df.sort_index()
        df["daily_return"] = df["Close"].pct_change()
        # 20거래일 평균 대비 거래량 비율
        df["avg_volume"] = df["Volume"].rolling(window=_LOOKBACK_DAYS).mean()
        df["volume_ratio"] = df["Volume"] / df["avg_volume"]

        for idx, row in df.iterrows():
            trade_date = idx.date() if hasattr(idx, "date") else idx
            if trade_date < start_date or trade_date > end_date:
                continue
            if pd.isna(row.get("volume_ratio", float("nan"))):
                continue

            results.append({
                "trade_date": trade_date,
                "krx_code": code,
                "signal": "buy" if row["volume_ratio"] > 1.0 else "hold",
                "price": float(row["Close"]),
                "return_pct": float(row["daily_return"]) if not pd.isna(row.get("daily_return", float("nan"))) else None,
            })

    return sorted(results, key=lambda x: x["trade_date"])


async def run_backtest(
    run_id: int,
    strategy: str,
    start_date: date,
    end_date: date,
    db_url: str,
) -> None:
    """백테스트 비동기 실행 — asyncio.create_task()로 호출.

    # @MX:WARN: [AUTO] 비동기 함수 내 동기 블로킹 코드 포함
    # @MX:REASON: FinanceDataReader는 동기 라이브러리 — run_in_executor로 래핑

    Args:
        run_id: backtest_runs.id
        strategy: "momentum" 또는 "volume"
        start_date: 시작일
        end_date: 종료일
        db_url: 동기 DB 연결 URL
    """
    logger.info("백테스트 시작 — run_id=%d, strategy=%s", run_id, strategy)

    # 동기 DB 세션 생성
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # 상태 업데이트: running
        _update_status(db, run_id, "running")

        # 가격 데이터 조회 (blocking → thread pool)
        loop = asyncio.get_event_loop()
        krx_codes = _get_krx_universe()
        price_data = await loop.run_in_executor(
            None, _fetch_price_data, krx_codes, start_date, end_date
        )

        # 전략 실행
        if strategy == "momentum":
            trade_records = _run_momentum_strategy(price_data, start_date, end_date)
        else:
            trade_records = _run_volume_strategy(price_data, start_date, end_date)

        # 결과 저장
        _save_results(db, run_id, trade_records)

        # 완료 상태 업데이트
        _update_status(db, run_id, "done", completed=True)
        logger.info("백테스트 완료 — run_id=%d, records=%d", run_id, len(trade_records))

    except Exception:
        logger.exception("백테스트 실패 — run_id=%d", run_id)
        _update_status(db, run_id, "error")
    finally:
        db.close()


def _update_status(db, run_id: int, status: str, completed: bool = False) -> None:
    """백테스트 실행 상태 업데이트"""
    from stock_picker.db.models import BacktestRun

    run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()
    if run is not None:
        run.status = status
        if completed:
            run.completed_at = datetime.now()
        db.commit()


def _save_results(db, run_id: int, records: list[dict]) -> None:
    """백테스트 일별 결과 일괄 저장"""
    from stock_picker.db.models import BacktestDailyResult

    for rec in records:
        result = BacktestDailyResult(
            run_id=run_id,
            trade_date=rec["trade_date"],
            krx_code=rec["krx_code"],
            signal=rec["signal"],
            price=rec["price"],
            return_pct=rec.get("return_pct"),
        )
        db.add(result)

    if records:
        db.commit()
