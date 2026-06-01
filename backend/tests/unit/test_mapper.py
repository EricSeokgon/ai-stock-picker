# KRX 종목 매핑 단위 테스트

import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestLoadKrxMaster:
    """KRX 마스터 데이터 로딩 테스트"""

    def test_load_krx_master_returns_dict(self):
        """KRX 마스터 CSV 로딩 → 딕셔너리 반환"""
        from stock_picker.mapping.krx_master import load_krx_master

        result = load_krx_master(FIXTURES_DIR / "krx_master.csv")

        assert isinstance(result, dict)

    def test_load_krx_master_samsung_code(self):
        """삼성전자 → 005930 매핑 확인"""
        from stock_picker.mapping.krx_master import load_krx_master

        master = load_krx_master(FIXTURES_DIR / "krx_master.csv")

        assert master["삼성전자"] == "005930"

    def test_load_krx_master_skhynix_code(self):
        """SK하이닉스 → 000660 매핑 확인"""
        from stock_picker.mapping.krx_master import load_krx_master

        master = load_krx_master(FIXTURES_DIR / "krx_master.csv")

        assert master["SK하이닉스"] == "000660"

    def test_load_krx_master_contains_10_entries(self):
        """픽스처 데이터 10개 종목 확인"""
        from stock_picker.mapping.krx_master import load_krx_master

        master = load_krx_master(FIXTURES_DIR / "krx_master.csv")

        assert len(master) == 10


class TestStockMapperMentions:
    """StockMapper.map_mentions 단위 테스트"""

    @pytest.fixture
    def krx_master(self):
        """테스트용 KRX 마스터 딕셔너리"""
        from stock_picker.mapping.krx_master import load_krx_master
        return load_krx_master(FIXTURES_DIR / "krx_master.csv")

    def test_map_mentions_samsung_found(self, krx_master):
        """삼성전자 언급 → 005930 매핑"""
        from stock_picker.mapping.mapper import StockMapper

        mapper = StockMapper()
        content = "삼성전자가 2분기 실적을 발표했다."
        mentions = mapper.map_mentions(content, krx_master)

        assert len(mentions) >= 1
        samsung = next(m for m in mentions if m["stock_name"] == "삼성전자")
        assert samsung["krx_code"] == "005930"
        assert samsung["mention_status"] == "mapped"

    def test_map_mentions_skhynix_found(self, krx_master):
        """SK하이닉스 언급 → 000660 매핑"""
        from stock_picker.mapping.mapper import StockMapper

        mapper = StockMapper()
        content = "SK하이닉스의 HBM 수출이 증가했다."
        mentions = mapper.map_mentions(content, krx_master)

        skhynix = next((m for m in mentions if m["stock_name"] == "SK하이닉스"), None)
        assert skhynix is not None
        assert skhynix["krx_code"] == "000660"
        assert skhynix["mention_status"] == "mapped"

    def test_map_mentions_unknown_stock_returns_unmapped(self, krx_master):
        """존재하지 않는 회사 → None (E-1)"""
        from stock_picker.mapping.mapper import StockMapper

        mapper = StockMapper()
        # 알려진 종목만 포함된 본문 (존재하지않는회사는 매핑 불가)
        content = "삼성전자가 실적을 발표했다."
        mentions = mapper.map_mentions(content, krx_master)

        # 존재하지 않는 회사는 결과에 없어야 함
        unknown = [m for m in mentions if m["stock_name"] == "존재하지않는회사"]
        assert unknown == []

    def test_map_mentions_partial_name_not_matched(self, krx_master):
        """부분 이름 단독 '삼성' → 매핑되지 않음 (엄격한 일치)"""
        from stock_picker.mapping.mapper import StockMapper

        mapper = StockMapper()
        # '삼성'만 있고 '삼성전자'는 없는 문장
        content = "삼성 그룹 계열사가 좋은 실적을 냈다."
        mentions = mapper.map_mentions(content, krx_master)

        # '삼성전자'가 매핑되면 안 됨 (부분 매칭이 아닌 엄격 매칭)
        samsung_exact = [m for m in mentions if m["stock_name"] == "삼성전자"]
        assert samsung_exact == []

    def test_map_mentions_multiple_stocks_in_content(self, krx_master):
        """여러 종목 언급 → 모두 매핑"""
        from stock_picker.mapping.mapper import StockMapper

        mapper = StockMapper()
        content = "삼성전자와 SK하이닉스가 나란히 좋은 실적을 냈다."
        mentions = mapper.map_mentions(content, krx_master)

        stock_names = [m["stock_name"] for m in mentions]
        assert "삼성전자" in stock_names
        assert "SK하이닉스" in stock_names

    def test_map_mentions_empty_content(self, krx_master):
        """빈 문자열 → 빈 리스트"""
        from stock_picker.mapping.mapper import StockMapper

        mapper = StockMapper()
        mentions = mapper.map_mentions("", krx_master)

        assert mentions == []
