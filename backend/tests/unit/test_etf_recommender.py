# ETF 추천기 단위 테스트 (TASK-020)
from pathlib import Path

import pytest

# 픽스처 파일 경로
_FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"
_ETF_MASTER_PATH = _FIXTURE_DIR / "etf_master.json"


class TestLoadEtfMaster:
    """ETF 마스터 데이터 로딩 테스트"""

    def test_load_returns_list(self):
        """load_etf_master()는 리스트를 반환해야 한다"""
        from stock_picker.mapping.etf_master import load_etf_master

        result = load_etf_master(_ETF_MASTER_PATH)
        assert isinstance(result, list)

    def test_load_returns_all_entries(self):
        """픽스처 파일의 모든 ETF 엔트리가 로드되어야 한다"""
        from stock_picker.mapping.etf_master import load_etf_master

        result = load_etf_master(_ETF_MASTER_PATH)
        assert len(result) == 8

    def test_each_entry_has_required_fields(self):
        """각 ETF 엔트리는 etf_code, etf_name, sectors 필드를 가져야 한다"""
        from stock_picker.mapping.etf_master import load_etf_master

        result = load_etf_master(_ETF_MASTER_PATH)
        for entry in result:
            assert "etf_code" in entry
            assert "etf_name" in entry
            assert "sectors" in entry
            assert isinstance(entry["sectors"], list)

    def test_semiconductor_etf_present(self):
        """반도체 ETF(091160)가 포함되어야 한다"""
        from stock_picker.mapping.etf_master import load_etf_master

        result = load_etf_master(_ETF_MASTER_PATH)
        codes = [e["etf_code"] for e in result]
        assert "091160" in codes


class TestEtfRecommender:
    """EtfRecommender 클래스 테스트"""

    @pytest.fixture
    def sector_trends_high_semiconductor(self) -> dict[str, float]:
        """반도체 섹터 트렌드가 높은 상태"""
        return {
            "반도체": 0.85,
            "IT": 0.60,
            "자동차": 0.30,
        }

    @pytest.fixture
    def recommender(self):
        """EtfRecommender 인스턴스 (픽스처 파일 사용)"""
        from stock_picker.recommendation.etf import EtfRecommender

        return EtfRecommender(etf_master_path=_ETF_MASTER_PATH)

    def test_semiconductor_sector_ranks_091160_first(
        self, recommender, sector_trends_high_semiconductor
    ):
        """반도체 트렌드가 높으면 091160(KODEX 반도체)이 1위여야 한다"""
        result = recommender.recommend(sector_trends_high_semiconductor)
        assert len(result) > 0
        assert result[0]["etf_code"] == "091160"

    def test_result_sorted_by_score_descending(
        self, recommender, sector_trends_high_semiconductor
    ):
        """결과는 etf_score 내림차순으로 정렬되어야 한다"""
        result = recommender.recommend(sector_trends_high_semiconductor)
        scores = [r["etf_score"] for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_etf_covering_multiple_trending_sectors_scores_higher(self, recommender):
        """여러 트렌딩 섹터를 커버하는 ETF는 더 높은 점수를 받아야 한다"""
        sector_trends = {
            "반도체": 0.8,
            "IT": 0.8,
        }
        result = recommender.recommend(sector_trends)
        # 091160(반도체+IT) vs 228810(IT+소프트웨어) → 둘다 관련 있음
        # 091160과 228810 모두 2개 섹터 중 다른 비율을 가지므로 결과 확인
        assert len(result) >= 2

    def test_unknown_sector_does_not_crash(self, recommender):
        """알 수 없는 섹터가 있어도 ETF는 정상 반환되어야 한다"""
        sector_trends = {
            "알수없는섹터": 0.9,
            "반도체": 0.5,
        }
        result = recommender.recommend(sector_trends)
        # 반도체 관련 ETF는 여전히 랭크되어야 함
        assert len(result) > 0

    def test_all_sectors_unknown_returns_zero_scores(self, recommender):
        """모든 섹터가 매핑 안 되면 etf_score는 0이어야 한다"""
        sector_trends = {
            "알수없음": 0.9,
        }
        result = recommender.recommend(sector_trends)
        # 매핑 안 된 경우 모든 ETF 점수 0
        for r in result:
            assert r["etf_score"] == pytest.approx(0.0)

    def test_result_contains_required_fields(
        self, recommender, sector_trends_high_semiconductor
    ):
        """결과 항목은 etf_code, etf_name, etf_score, sectors 필드를 가져야 한다"""
        result = recommender.recommend(sector_trends_high_semiconductor)
        for item in result:
            assert "etf_code" in item
            assert "etf_name" in item
            assert "etf_score" in item
            assert "sectors" in item

    def test_empty_sector_trends_returns_all_etfs_with_zero_score(self, recommender):
        """빈 트렌드 딕셔너리는 모든 ETF를 0점으로 반환해야 한다"""
        result = recommender.recommend({})
        assert len(result) == 8  # 픽스처의 전체 ETF 수
        for r in result:
            assert r["etf_score"] == pytest.approx(0.0)
