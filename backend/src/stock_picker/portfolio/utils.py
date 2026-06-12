# KRX 코드 prefix → 섹터 매핑 공용 유틸리티 (SPEC-STOCK-017)
# ai_analysis.py 와 advice/service.py 에서 중복 정의되던 함수를 단일 출처로 통합
from __future__ import annotations

# @MX:ANCHOR: [AUTO] get_sector — ai_analysis, advice.service, portfolio.service 3곳에서 호출
# @MX:REASON: [AUTO] KRX 코드 prefix 매핑 규칙은 전체 도메인 공통 계약이므로 단일 출처 필요 (SPEC-STOCK-017)
# @MX:SPEC: SPEC-STOCK-017 REQ-PERF-004

# prefix 길이가 긴 규칙부터 순서대로 배치해야 올바르게 매칭됨
_SECTOR_MAP: dict[str, str] = {
    "00594": "IT/반도체",
    "005": "전자/반도체",
    "006": "화학",
    "007": "철강/금속",
    "008": "건설",
    "009": "기계",
    "000": "화학",
    "00": "금융",
    "01": "자동차",
    "02": "에너지",
    "03": "통신",
    "04": "유통/소비재",
    "05": "바이오/제약",
    "06": "금융",
    "07": "IT/서비스",
    "08": "미디어/엔터",
    "09": "건설/부동산",
}


def get_sector(krx_code: str) -> str:
    """KRX 코드 prefix 로 섹터명을 반환합니다.

    prefix 길이가 긴 규칙을 우선 적용하고, 일치하는 prefix 가 없으면 '기타' 반환.

    Args:
        krx_code: 종목 코드 (예: "005930", "000660")

    Returns:
        섹터명 문자열 (예: "전자/반도체", "금융", "기타")
    """
    for key, sector in _SECTOR_MAP.items():
        if krx_code.startswith(key):
            return sector
    return "기타"
