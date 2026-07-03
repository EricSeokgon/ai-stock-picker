# FX 환율 서비스 — USD/KRW 실시간 조회 + Redis TTL 캐시 (SPEC-STOCK-028)
# dividends.py 패턴 재사용: run_in_executor로 동기 FDR 격리 + redis.asyncio 캐시
# @MX:NOTE: [AUTO] DB 테이블 의존 없음 — FDR 실시간 조회 + Redis TTL 3600s
# @MX:SPEC: SPEC-STOCK-028 REQ-FA-003
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

import FinanceDataReader as fdr  # noqa: N813

logger = logging.getLogger(__name__)

# KST = UTC+9
_KST = timezone(timedelta(hours=9))
# Redis 캐시 TTL: 1시간 (환율은 하루치 캐시보다 짧게)
_FX_TTL = 3600
# FDR/Redis 모두 실패 시 사용하는 폴백 환율
_FALLBACK_RATE = 1350.0


def _today_kst() -> str:
    """KST 기준 오늘 날짜 문자열 (YYYY-MM-DD) 반환."""
    return datetime.now(_KST).strftime("%Y-%m-%d")


def _fetch_usd_krw_sync() -> float:
    """동기 FDR USD/KRW 환율 조회 (스레드 풀에서 실행).

    # @MX:NOTE: [AUTO] 동기 FDR 호출 — run_in_executor에서만 호출할 것
    FDR DataReader('USD/KRW')로 최근 거래일 종가를 가져온다.
    데이터 부재 시 예외를 상위로 전파하여 호출자가 폴백 처리하도록 함.

    Returns:
        float: 최근 USD/KRW 환율
    """
    df = fdr.DataReader("USD/KRW")
    if df is None or df.empty:
        raise ValueError("FDR USD/KRW 데이터 없음")
    # 마지막 행 종가(Close 또는 첫 번째 숫자형 컬럼)
    close_col = "Close" if "Close" in df.columns else df.select_dtypes("number").columns[0]
    return float(df[close_col].iloc[-1])


# @MX:ANCHOR: [AUTO] USD/KRW 환율 조회 단일 진입점
# @MX:REASON: service.py(calculate_performance), T-006 해외 자산 환산 등 3개 이상 호출처
async def get_usd_krw_rate(redis: Any) -> float:
    """USD/KRW 환율 조회 — Redis 캐시 + FDR + 폴백 상수.

    캐시 키: fx:USD:KRW:{today_kst}, TTL=3600s.
    Redis 또는 FDR 장애 시 _FALLBACK_RATE=1350.0 반환 (graceful degradation).

    Args:
        redis: redis.asyncio 클라이언트

    Returns:
        float: USD/KRW 환율 (실패 시 _FALLBACK_RATE)
    """
    today = _today_kst()
    cache_key = f"fx:USD:KRW:{today}"

    # Redis 캐시 조회
    try:
        cached = await redis.get(cache_key)
        if cached is not None:
            return float(cached)
    except Exception as e:
        logger.warning("Redis FX 캐시 조회 실패 — FDR fallback: %s", e)

    # FDR 동기 조회를 스레드 풀에서 실행
    try:
        loop = asyncio.get_event_loop()
        rate = await loop.run_in_executor(None, _fetch_usd_krw_sync)
    except Exception as e:
        logger.warning("FDR USD/KRW 조회 실패 — 폴백 환율 %s 사용: %s", _FALLBACK_RATE, e)
        return _FALLBACK_RATE

    # Redis 캐시 저장 (실패해도 결과 반환)
    try:
        await redis.setex(cache_key, _FX_TTL, str(rate))
    except Exception as e:
        logger.warning("Redis FX 캐시 저장 실패: %s", e)

    return rate
