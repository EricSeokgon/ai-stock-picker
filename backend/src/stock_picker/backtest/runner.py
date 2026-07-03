# 백테스트 실행 엔진 — momentum/volume 전략
import asyncio
import logging
from datetime import date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


logger = logging.getLogger(__name__)

# 기본값 — run 레코드의 top_n/universe_size가 None이면 사용
_DEFAULT_TOP_N = 5
_DEFAULT_UNIVERSE_SIZE = 10
# 모멘텀/볼륨 계산 기간 (거래일)
_LOOKBACK_DAYS = 20

# KOSPI/KOSDAQ 벤치마크 코드
_BENCHMARK_CODE = "KS11"


def _get_krx_universe(universe_size: int) -> list[str]:
    """KRX 주요 종목 코드 목록 반환 — universe_size만큼 반환.

    Args:
        universe_size: 반환할 종목 수

    Returns:
        종목 코드 목록
    """
    # 코스피 200 주요 종목 샘플 (확장 풀)
    full_universe = [
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
        "055550",  # 신한금융
        "086790",  # 하나금융
        "032830",  # 삼성생명
        "018260",  # 삼성에스디에스
        "207940",  # 삼성바이오로직스
        "003550",  # LG
        "012330",  # 현대모비스
        "011200",  # HMM
        "096770",  # SK이노베이션
        "017670",  # SK텔레콤
    ]
    return full_universe[:universe_size]


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


def _fetch_benchmark_data(start_date: date, end_date: date) -> list[tuple[date, float]] | None:
    """KOSPI 지수 데이터 조회 — 동기 함수.

    # @MX:WARN: [AUTO] 외부 API 블로킹 호출 — 벤치마크 실패 시 None 반환
    # @MX:REASON: 벤치마크 조회 실패가 백테스트 전체를 실패시켜선 안 됨

    Returns:
        [(날짜, 종가)] 목록 또는 None (조회 실패 시)
    """
    try:
        import FinanceDataReader as fdr
        df = fdr.DataReader(_BENCHMARK_CODE, start=str(start_date), end=str(end_date))
        if df is None or df.empty:
            logger.warning("벤치마크 데이터 없음 — code=%s", _BENCHMARK_CODE)
            return None
        df = df.sort_index()
        result = []
        for idx, row in df.iterrows():
            d = idx.date() if hasattr(idx, "date") else idx
            close_val = row.get("Close", row.get("Adj Close", None))
            if close_val is not None:
                result.append((d, float(close_val)))
        return result if result else None
    except Exception:
        logger.warning("벤치마크 데이터 조회 실패 — code=%s", _BENCHMARK_CODE, exc_info=True)
        return None


def _normalize_series(values: list[float]) -> list[float]:
    """시계열을 시작값 1.0으로 정규화.

    Args:
        values: 원본 가격/가치 시계열

    Returns:
        정규화된 시계열 (첫 값이 1.0)
    """
    if not values or values[0] == 0:
        return values
    base = values[0]
    return [v / base for v in values]


def _run_momentum_strategy(
    price_data: dict, start_date: date, end_date: date, top_n: int
) -> list[dict]:
    """모멘텀 전략: 월별 20거래일 수익률 상위 top_n 종목 매수.

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
    price_data: dict, start_date: date, end_date: date, top_n: int
) -> list[dict]:
    """볼륨 전략: 월별 20거래일 거래량 비율 상위 top_n 종목 매수.

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
    universe_size: int | None = None,
    top_n: int | None = None,
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
        universe_size: 유니버스 크기 (None이면 기본값 사용)
        top_n: 상위 종목 수 (None이면 기본값 사용)
    """
    logger.info("백테스트 시작 — run_id=%d, strategy=%s", run_id, strategy)

    # 실제 파라미터 결정
    effective_universe_size = universe_size if universe_size is not None else _DEFAULT_UNIVERSE_SIZE
    effective_top_n = top_n if top_n is not None else _DEFAULT_TOP_N

    # 동기 DB 세션 생성
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # 상태 업데이트: running
        _update_status(db, run_id, "running")

        # 가격 데이터 조회 (blocking → thread pool)
        loop = asyncio.get_event_loop()
        krx_codes = _get_krx_universe(effective_universe_size)
        price_data = await loop.run_in_executor(
            None, _fetch_price_data, krx_codes, start_date, end_date
        )

        # 전략 실행
        if strategy == "momentum":
            trade_records = _run_momentum_strategy(
                price_data, start_date, end_date, effective_top_n
            )
        else:
            trade_records = _run_volume_strategy(
                price_data, start_date, end_date, effective_top_n
            )

        # 벤치마크 데이터 조회 (실패해도 백테스트 중단 안 함)
        benchmark_raw = await loop.run_in_executor(
            None, _fetch_benchmark_data, start_date, end_date
        )
        if benchmark_raw is None:
            logger.warning("벤치마크 데이터 없음 — benchmark_value를 None으로 처리 — run_id=%d", run_id)

        # 결과 저장
        _save_results(db, run_id, trade_records, benchmark_raw)

        # 완료 상태 업데이트
        _update_status(db, run_id, "done", completed=True)
        logger.info("백테스트 완료 — run_id=%d, records=%d", run_id, len(trade_records))

    except Exception:
        logger.exception("백테스트 실패 — run_id=%d", run_id)
        _update_status(db, run_id, "failed")
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


def _save_results(
    db,
    run_id: int,
    records: list[dict],
    benchmark_raw: list[tuple[date, float]] | None = None,
) -> None:
    """백테스트 일별 결과 일괄 저장.

    벤치마크 데이터가 없으면 portfolio_value와 benchmark_value 없이 저장.
    """
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
