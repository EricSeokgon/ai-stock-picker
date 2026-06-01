# FinanceDataReader 비동기 래퍼 (동기 라이브러리 격리)
# REQ-PRICE-001: 스레드 풀을 통해 동기 라이브러리를 비동기 컨텍스트에서 격리
import asyncio
from datetime import datetime, timedelta
from typing import Any

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
