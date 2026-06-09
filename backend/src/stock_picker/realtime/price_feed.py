# 단일 종목 현재가 조회 및 최신 가격 캐시 (REQ-WS-003, REQ-WS-007)
# 캐시 구조: {krx_code: {"price": float, "change_pct": float, "timestamp": str}}
# FinanceDataReader로 현재가와 전일 종가 조회하여 등락률 계산
import logging
from datetime import datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# @MX:WARN: [AUTO] 모듈 수준 가변 전역 상태 — 캐시 딕셔너리
# @MX:REASON: 가격 캐시는 스레드 간 공유되므로 동시 쓰기 시 경쟁 조건 가능

_price_cache: dict[str, dict[str, Any]] = {}


def get_current_price(krx_code: str) -> dict[str, Any] | None:
    """단일 종목 현재가 조회.

    # @MX:ANCHOR: [AUTO] 가격 조회 단일 진입점 — WebSocket 라우터에서 호출
    # @MX:REASON: ws_router.py에서 직접 호출, 캐시 포함 외부 API 격리 담당

    FinanceDataReader로 최근 2일 데이터를 조회하여 현재가와 등락률을 계산한다.
    성공 시 캐시에 저장 후 반환, 실패 시 None 반환.

    Args:
        krx_code: KRX 종목코드 (예: "005930")

    Returns:
        {"krx_code": str, "price": float, "change_pct": float, "timestamp": str}
        조회 실패 시 None
    """
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

        # 캐시 갱신
        _price_cache[krx_code] = result
        return result

    except Exception:
        logger.exception("현재가 조회 실패 — krx_code=%s", krx_code)
        return None
