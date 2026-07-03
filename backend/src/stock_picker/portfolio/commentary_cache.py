# SPEC-STOCK-040: 포트폴리오 코멘터리 인메모리 TTL 캐시
# @MX:NOTE: [AUTO] scipy 금지·신규 마이그레이션 없음·인메모리 캐시만 (SPEC-STOCK-040)
# @MX:NOTE: [AUTO] 단일 워커 프로세스 가정 — 멀티 워커 환경에서는 캐시 공유 불가

import time

# @MX:WARN: [AUTO] 전역 가변 상태 — 단일 워커 가정, 멀티 프로세스 환경 비적합
# @MX:REASON: 인메모리 캐시는 프로세스 로컬 상태; Redis 없이 설계된 SPEC-STOCK-040 제약 준수

_CACHE: dict[int, dict] = {}
# TTL: 300초 (5분)
_TTL = 300


def get_cached_commentary(portfolio_id: int) -> str | None:
    """캐시에서 포트폴리오 코멘터리를 조회한다.

    TTL(300초) 초과 시 None 반환 (만료 처리).
    """
    entry = _CACHE.get(portfolio_id)
    if entry is None:
        return None
    # TTL 만료 확인 — time 모듈 속성으로 접근해야 mock 가능
    if time.time() - entry["ts"] > _TTL:
        return None
    return entry["commentary"]


def set_cached_commentary(portfolio_id: int, commentary: str) -> None:
    """포트폴리오 코멘터리를 캐시에 저장한다.

    이미 존재하면 덮어쓴다 (갱신).
    """
    _CACHE[portfolio_id] = {
        "commentary": commentary,
        "ts": time.time(),
    }
