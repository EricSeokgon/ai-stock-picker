# 단일 종목 현재가 조회 및 최신 가격 캐시 (REQ-WS-003, REQ-WS-007)
# 캐시 구조: {krx_code: {"price": float, "change_pct": float, "timestamp": str}}
# FinanceDataReader로 현재가와 전일 종가 조회하여 등락률 계산
# Redis 캐시(TTL 60초)를 우선 조회하고, 미스 시 FinanceDataReader로 폴백
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# @MX:WARN: [AUTO] 모듈 수준 가변 전역 상태 — 캐시 딕셔너리
# @MX:REASON: 가격 캐시는 스레드 간 공유되므로 동시 쓰기 시 경쟁 조건 가능

_price_cache: dict[str, dict[str, Any]] = {}

_PRICE_REDIS_TTL = 60  # 가격 Redis 캐시 TTL(초)


def _get_redis_price_client():
    """가격 캐시용 동기 Redis 클라이언트 반환.

    REDIS_URL 환경변수를 사용한다. 접속 실패 시 None 반환.
    """
    try:
        import redis

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        client = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=1)
        return client
    except Exception as e:
        logger.warning("Redis 클라이언트 생성 실패 (폴백): %s", e)
        return None


def get_current_price(krx_code: str) -> dict[str, Any] | None:
    """단일 종목 현재가 조회.

    # @MX:ANCHOR: [AUTO] 가격 조회 단일 진입점 — WebSocket 라우터에서 호출
    # @MX:REASON: ws_router.py에서 직접 호출, 캐시 포함 외부 API 격리 담당

    조회 순서:
    1. Redis 캐시 키 "price:{krx_code}" 확인 (TTL 60초)
    2. Redis 히트: 즉시 반환
    3. Redis 미스/오류: FinanceDataReader로 조회
    4. 조회 성공 시 Redis에 60초 TTL로 저장
    5. 결과 반환 (실패 시 None)

    Args:
        krx_code: KRX 종목코드 (예: "005930")

    Returns:
        {"krx_code": str, "price": float, "change_pct": float, "timestamp": str}
        조회 실패 시 None
    """
    redis_key = f"price:{krx_code}"

    # 1단계: Redis 캐시 조회 시도
    redis_client = _get_redis_price_client()
    if redis_client is not None:
        try:
            cached_raw = redis_client.get(redis_key)
            if cached_raw is not None:
                logger.debug("가격 Redis 캐시 히트 — krx_code=%s", krx_code)
                return json.loads(cached_raw)
        except Exception as e:
            logger.warning("가격 Redis 읽기 실패 (폴백): %s", e)

    # 2단계: FinanceDataReader로 조회
    try:
        import FinanceDataReader as fdr  # noqa: N813

        end = datetime.now()
        start = end - timedelta(days=5)  # 최근 5일치 조회 (휴장일 고려)

        df = fdr.DataReader(krx_code, start, end)

        if df is None or df.empty:
            logger.warning("가격 데이터 없음 — krx_code=%s", krx_code)
            return None

        close_col = "Close" if "Close" in df.columns else df.columns[-1]
        current_price = float(df[close_col].iloc[-1])

        # 등락률 계산: 전일 종가 대비
        if len(df) >= 2:
            prev_price = float(df[close_col].iloc[-2])
            change_pct = ((current_price - prev_price) / prev_price * 100) if prev_price > 0 else 0.0
        else:
            # 데이터가 1건이면 등락률 0
            change_pct = 0.0

        result: dict[str, Any] = {
            "krx_code": krx_code,
            "price": current_price,
            "change_pct": round(change_pct, 2),
            "timestamp": datetime.now().isoformat(),
        }

        # 캐시 갱신 (인메모리)
        _price_cache[krx_code] = result

        # Redis 캐시 저장 시도
        if redis_client is not None:
            try:
                redis_client.set(
                    redis_key,
                    json.dumps(result, ensure_ascii=False),
                    ex=_PRICE_REDIS_TTL,
                )
                logger.debug("가격 Redis 캐시 저장 — krx_code=%s", krx_code)
            except Exception as e:
                logger.warning("가격 Redis 쓰기 실패 (폴백): %s", e)

        return result

    except Exception:
        logger.exception("현재가 조회 실패 — krx_code=%s", krx_code)
        return None
