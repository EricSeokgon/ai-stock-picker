# FinanceDataReader 비동기 래퍼 (동기 라이브러리 격리)
# REQ-PRICE-001: 스레드 풀을 통해 동기 라이브러리를 비동기 컨텍스트에서 격리
import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Any

import redis.asyncio as aioredis
import structlog

log = structlog.get_logger()


async def get_stock_price_data(krx_code: str) -> dict[str, Any] | None:
    """종목 시세 조회 (executor로 동기 라이브러리 격리).

    # @MX:ANCHOR: [AUTO] 시세 조회 단일 진입점 - 추천 서비스와 집계기에서 호출
    # @MX:REASON: RecommendationService, StockAggregator에서 공유 사용
    # @MX:WARN: [AUTO] run_in_executor 사용 - 스레드 풀 자원 소비
    # @MX:REASON: FinanceDataReader는 동기 라이브러리이므로 스레드 풀 격리 필수

    Args:
        krx_code: KRX 종목코드 (예: "005930")

    Returns:
        {"close_price": float, "change_rate": float, "volume": int} 딕셔너리.
        조회 실패 시 None 반환 (E-5).
    """
    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(None, _fetch_price, krx_code)
    except Exception as e:
        # 시세 실패 시 None 반환 - 파이프라인 중단 없음 (E-5)
        log.warning("시세 조회 실패", krx_code=krx_code, error=str(e))
        return None


_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


async def get_stock_price_history(
    krx_code: str,
    days: int = 30,
) -> list[dict]:
    """종목 일별 종가 히스토리 반환 (최근 N일).

    # @MX:WARN: [AUTO] Redis 캐시 + run_in_executor 조합 — 장애 격리 필수
    # @MX:REASON: Redis 장애 또는 FDR 실패 시 빈 리스트 반환으로 graceful degradation

    캐시 키: stock_prices:{krx_code}:{days}, TTL 3600s.
    FinanceDataReader 실패 또는 Redis 장애 시 [] 반환 (예외 전파 없음).

    Args:
        krx_code: KRX 종목코드 (예: "005930")
        days: 조회 기간 (일수)

    Returns:
        [{"date": "YYYY-MM-DD", "close": float}, ...] — 오래된 날짜부터 정렬.
        실패 시 빈 리스트.
    """
    cache_key = f"stock_prices:{krx_code}:{days}"

    # Redis 캐시 조회 (실패해도 계속 진행)
    redis_client: aioredis.Redis | None = None
    try:
        redis_client = aioredis.from_url(_REDIS_URL, decode_responses=True)
        cached = await redis_client.get(cache_key)
        if cached is not None:
            return json.loads(cached)
    except Exception:
        log.warning("Redis 캐시 조회 실패 — FinanceDataReader로 폴백", krx_code=krx_code)

    # FinanceDataReader 조회
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(None, _fetch_price_history, krx_code, days)
    except Exception as e:
        log.warning("주가 히스토리 조회 실패", krx_code=krx_code, error=str(e))
        if redis_client:
            try:
                await redis_client.aclose()
            except Exception:
                pass
        return []

    if not result:
        if redis_client:
            try:
                await redis_client.aclose()
            except Exception:
                pass
        return []

    # Redis 캐시 저장 (실패해도 결과는 반환)
    try:
        if redis_client:
            await redis_client.set(cache_key, json.dumps(result), ex=3600)
    except Exception:
        log.warning("Redis 캐시 저장 실패", krx_code=krx_code)
    finally:
        if redis_client:
            try:
                await redis_client.aclose()
            except Exception:
                pass

    return result


def _fetch_price_history(krx_code: str, days: int) -> list[dict]:
    """동기 주가 히스토리 조회 (스레드 풀에서 실행).

    Args:
        krx_code: KRX 종목코드
        days: 조회 기간 (일수)

    Returns:
        날짜별 종가 리스트. 데이터 없으면 빈 리스트.
    """
    import FinanceDataReader as fdr  # noqa: N813

    end = datetime.now()
    start = end - timedelta(days=days)

    try:
        df = fdr.DataReader(krx_code, start, end)
    except Exception:
        return []

    if df is None or df.empty:
        return []

    result: list[dict] = []
    for idx, row in df.iterrows():
        date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
        close_val = row.get("Close", row.get("close", None))
        if close_val is None:
            continue
        result.append({"date": date_str, "close": float(close_val)})

    # 오래된 날짜부터 정렬
    result.sort(key=lambda x: x["date"])
    return result


def _fetch_price(krx_code: str) -> dict[str, Any] | None:
    """동기 시세 조회 (스레드 풀에서 실행).

    Args:
        krx_code: KRX 종목코드

    Returns:
        시세 딕셔너리. 데이터 없으면 None.
    """
    import FinanceDataReader as fdr  # noqa: N813 - 라이브러리 명명 규칙 준수

    end = datetime.now()
    start = end - timedelta(days=30)

    df = fdr.DataReader(krx_code, start, end)

    if df is None or df.empty:
        return None

    # 최신 데이터 기준
    latest = df.iloc[-1]

    return {
        "close_price": float(latest.get("Close", latest.get("close", 0.0))),
        "change_rate": float(latest.get("Change", latest.get("change", 0.0))),
        "volume": int(latest.get("Volume", latest.get("volume", 0))),
    }
