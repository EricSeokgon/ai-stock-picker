# SPEC-STOCK-017 섹터 유틸리티 단위 테스트
import pytest

from stock_picker.portfolio.utils import get_sector


class TestGetSector:
    """get_sector 함수 — KRX 코드 prefix 매핑 검증"""

    @pytest.mark.parametrize("krx_code,expected", [
        ("005930", "전자/반도체"),   # 삼성전자
        ("005380", "전자/반도체"),   # 현대차 (005 prefix 매칭 확인)
        ("000660", "화학"),          # SK하이닉스 — 000 prefix
        ("006400", "화학"),          # 삼성SDI
        ("007070", "철강/금속"),     # GS리테일
        ("008000", "건설"),          # 이삭엔지니어링
        ("009780", "기계"),
        ("012330", "자동차"),        # 현대모비스 — 01 prefix
        ("034020", "통신"),          # 두산에너빌리티 — 03 prefix → 통신
        ("005490", "전자/반도체"),   # POSCO — 005 prefix
        ("051910", "바이오/제약"),   # LG화학 — 05 prefix
        ("066570", "금융"),          # LG전자 — 06 prefix
        ("078930", "IT/서비스"),     # GS — 07 prefix
        ("035420", "통신"),          # NAVER — 03 prefix → 통신
        ("999999", "기타"),          # 알 수 없는 코드
        ("", "기타"),                # 빈 문자열
    ])
    def test_sector_mapping(self, krx_code: str, expected: str):
        """KRX 코드에서 섹터를 올바르게 매핑한다"""
        assert get_sector(krx_code) == expected

    def test_unknown_prefix_returns_others(self):
        """매핑되지 않는 prefix → '기타'"""
        assert get_sector("99999") == "기타"

    def test_short_code_does_not_crash(self):
        """짧은 코드도 오류 없이 처리"""
        result = get_sector("0")
        assert isinstance(result, str)
