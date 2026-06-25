"""KRX 장중 판정 순수 함수 — SPEC-STOCK-039.

외부 의존 없이 datetime + zoneinfo 표준 라이브러리만 사용한다.
scipy 사용 금지 (HARD 제약).
"""
from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

# 한국 시간대 상수
_KST = ZoneInfo("Asia/Seoul")

# KRX 정규장 시간 경계
_OPEN = time(9, 0, 0)
_CLOSE = time(15, 30, 0)


# @MX:ANCHOR: [AUTO] is_krx_open — KRX 장중 판정 순수 함수 (fan_in >= 3)
# @MX:REASON: [AUTO] 엔드포인트(router), 단위 테스트, 폴링 훅에서 3곳 이상 참조 (SPEC-039)
def is_krx_open(now: datetime) -> bool:
    """KRX 정규장 개장 여부 반환.

    평일(월-금) 09:00:00 ≤ now ≤ 15:30:00 KST → True
    주말 또는 시간 외 → False

    Args:
        now: 판정 기준 시각 (timezone-aware datetime).
             UTC 등 다른 시간대도 허용하며 KST로 변환하여 판정한다.

    Returns:
        True이면 KRX 정규장 중.
    """
    # 입력 시각을 KST로 변환
    now_kst = now.astimezone(_KST)

    # 주말(토=5, 일=6)이면 False
    if now_kst.weekday() >= 5:
        return False

    # 장 시간 경계 판정 (경계 포함)
    t = now_kst.time()
    return _OPEN <= t <= _CLOSE
