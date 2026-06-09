# 추천 필터/정렬 API 통합 테스트 (SPEC-STOCK-005 TASK-005~007)
# TestClient + Redis mock 사용
import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


# ─── 헬퍼 ───────────────────────────────────────────────────────────────────


def _sample_recommendations() -> list[dict]:
    """테스트용 추천 리스트 (5개, 점수 다양, sector 포함)."""
    return [
        {
            "rank": 1,
            "krx_code": "005930",
            "total_score": 0.95,
            "sentiment_score": 0.90,
            "volume_score": 0.80,
            "momentum_score": 0.70,
            "anomaly_score": 0.60,
            "reasoning": "삼성전자 분석",
            "sector": "IT",
        },
        {
            "rank": 2,
            "krx_code": "000660",
            "total_score": 0.85,
            "sentiment_score": 0.75,
            "volume_score": 0.65,
            "momentum_score": 0.55,
            "anomaly_score": 0.45,
            "reasoning": "SK하이닉스 분석",
            "sector": "IT",
        },
        {
            "rank": 3,
            "krx_code": "055550",
            "total_score": 0.70,
            "sentiment_score": 0.60,
            "volume_score": 0.50,
            "momentum_score": 0.40,
            "anomaly_score": 0.30,
            "reasoning": "신한금융 분석",
            "sector": "금융",
        },
        {
            "rank": 4,
            "krx_code": "035420",
            "total_score": 0.60,
            "sentiment_score": 0.50,
            "volume_score": 0.40,
            "momentum_score": 0.30,
            "anomaly_score": 0.20,
            "reasoning": "NAVER 분석",
            "sector": "IT",
        },
        {
            "rank": 5,
            "krx_code": "096770",
            "total_score": 0.50,
            "sentiment_score": 0.40,
            "volume_score": 0.30,
            "momentum_score": 0.20,
            "anomaly_score": 0.10,
            "reasoning": "SK이노베이션 분석",
            "sector": "에너지",
        },
    ]


def _make_client_with_cache(cached_data: list | None) -> tuple:
    """캐시 데이터가 세팅된 TestClient 반환."""
    from stock_picker.api.main import create_app
    from stock_picker.recommendation.cache import RecommendationCache

    mock_cache = AsyncMock(spec=RecommendationCache)

    # get: 기본 캐시 반환
    mock_cache.get.return_value = cached_data
    # get_derived: 항상 미스
    mock_cache.get_derived.return_value = None
    # set_derived: 무시
    mock_cache.set_derived.return_value = None
    # build_derived_key: 실제 메서드 사용
    real_cache = RecommendationCache(AsyncMock())
    mock_cache.build_derived_key.side_effect = real_cache.build_derived_key

    app = create_app()

    # get_cache 의존성 주입 오버라이드
    from stock_picker.api.deps import get_cache

    async def override_get_cache():
        yield mock_cache

    app.dependency_overrides[get_cache] = override_get_cache

    client = TestClient(app)
    return client, mock_cache


# ─── 하위 호환성 테스트 ───────────────────────────────────────────────────────


class TestDefaultBehavior:
    """파라미터 없는 기본 호출은 기존 동작과 동일해야 한다."""

    def test_default_call_returns_recommendations(self) -> None:
        """파라미터 없이 호출 시 추천 목록 반환 (AC-7 하위 호환)."""
        client, _ = _make_client_with_cache(_sample_recommendations())

        response = client.get("/recommendations")

        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert len(data["recommendations"]) == 5

    def test_default_call_returns_preparing_when_no_data(self) -> None:
        """데이터 없을 때 preparing 상태 반환 (AC-10 하위 호환)."""
        client, _ = _make_client_with_cache(None)

        response = client.get("/recommendations")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "preparing"

    def test_default_call_does_not_use_derived_cache(self) -> None:
        """기본 호출은 파생 캐시를 조회하지 않는다."""
        client, mock_cache = _make_client_with_cache(_sample_recommendations())

        client.get("/recommendations")

        # 기본 파라미터 호출은 get_derived를 호출하지 않음
        mock_cache.get_derived.assert_not_called()


# ─── 정렬 테스트 ──────────────────────────────────────────────────────────────


class TestSortParameter:
    def test_sort_by_sentiment_returns_sorted_descending(self) -> None:
        """?sort=sentiment 시 sentiment_score 내림차순 정렬."""
        client, _ = _make_client_with_cache(_sample_recommendations())

        response = client.get("/recommendations?sort=sentiment")

        assert response.status_code == 200
        recs = response.json()["recommendations"]
        scores = [r["sentiment_score"] for r in recs]
        assert scores == sorted(scores, reverse=True), "sentiment_score 내림차순이어야 함"

    def test_sort_by_volume_returns_sorted_descending(self) -> None:
        """?sort=volume 시 volume_score 내림차순 정렬."""
        client, _ = _make_client_with_cache(_sample_recommendations())

        response = client.get("/recommendations?sort=volume")

        assert response.status_code == 200
        recs = response.json()["recommendations"]
        scores = [r["volume_score"] for r in recs]
        assert scores == sorted(scores, reverse=True), "volume_score 내림차순이어야 함"

    def test_sort_by_score_returns_sorted_descending(self) -> None:
        """?sort=score 시 total_score 내림차순 정렬."""
        client, _ = _make_client_with_cache(_sample_recommendations())

        response = client.get("/recommendations?sort=score")

        assert response.status_code == 200
        recs = response.json()["recommendations"]
        scores = [r["total_score"] for r in recs]
        assert scores == sorted(scores, reverse=True), "total_score 내림차순이어야 함"

    def test_invalid_sort_returns_422(self) -> None:
        """유효하지 않은 sort 값은 422 반환."""
        client, _ = _make_client_with_cache(_sample_recommendations())

        response = client.get("/recommendations?sort=invalid")

        assert response.status_code == 422


# ─── min_score 필터 테스트 ────────────────────────────────────────────────────


class TestMinScoreFilter:
    def test_min_score_filters_low_score_items(self) -> None:
        """?min_score=0.9 시 total_score >= 0.9인 항목만 반환."""
        client, _ = _make_client_with_cache(_sample_recommendations())

        response = client.get("/recommendations?min_score=0.9")

        assert response.status_code == 200
        recs = response.json()["recommendations"]
        # total_score 0.95인 항목만 통과
        assert len(recs) == 1
        assert recs[0]["krx_code"] == "005930"

    def test_min_score_returns_empty_list_when_no_match(self) -> None:
        """모든 항목이 필터에 걸리면 빈 리스트와 200 반환."""
        client, _ = _make_client_with_cache(_sample_recommendations())

        response = client.get("/recommendations?min_score=0.99")

        assert response.status_code == 200
        data = response.json()
        assert data["recommendations"] == []


# ─── limit 테스트 ─────────────────────────────────────────────────────────────


class TestLimitParameter:
    def test_limit_restricts_result_count(self) -> None:
        """?limit=3 시 최대 3개 반환."""
        client, _ = _make_client_with_cache(_sample_recommendations())

        response = client.get("/recommendations?limit=3")

        assert response.status_code == 200
        recs = response.json()["recommendations"]
        assert len(recs) == 3

    def test_limit_zero_returns_422(self) -> None:
        """limit=0은 422 반환 (gt=0 검증)."""
        client, _ = _make_client_with_cache(_sample_recommendations())

        response = client.get("/recommendations?limit=0")

        assert response.status_code == 422

    def test_limit_negative_returns_422(self) -> None:
        """음수 limit은 422 반환."""
        client, _ = _make_client_with_cache(_sample_recommendations())

        response = client.get("/recommendations?limit=-1")

        assert response.status_code == 422


# ─── 섹터 필터 테스트 ─────────────────────────────────────────────────────────


class TestSectorFilter:
    def test_sector_filter_returns_matching_items(self) -> None:
        """?sector=IT 시 sector=IT인 항목만 반환."""
        client, _ = _make_client_with_cache(_sample_recommendations())

        response = client.get("/recommendations?sector=IT")

        assert response.status_code == 200
        recs = response.json()["recommendations"]
        # IT 섹터: 005930, 000660, 035420 → 3개
        assert len(recs) == 3
        for rec in recs:
            # RecommendationItem에는 sector 필드가 없으므로 krx_code로 검증
            assert rec["krx_code"] in ["005930", "000660", "035420"]

    def test_sector_filter_nonexistent_returns_empty(self) -> None:
        """존재하지 않는 섹터 필터는 빈 리스트와 200 반환."""
        client, _ = _make_client_with_cache(_sample_recommendations())

        response = client.get("/recommendations?sector=존재하지않는섹터")

        assert response.status_code == 200
        data = response.json()
        assert data["recommendations"] == []


# ─── 복합 파라미터 테스트 ─────────────────────────────────────────────────────


class TestCombinedParameters:
    def test_limit_and_sort_combined(self) -> None:
        """limit=2&sort=sentiment 조합 동작."""
        client, _ = _make_client_with_cache(_sample_recommendations())

        response = client.get("/recommendations?limit=2&sort=sentiment")

        assert response.status_code == 200
        recs = response.json()["recommendations"]
        assert len(recs) == 2
        # sentiment_score 내림차순 상위 2개
        assert recs[0]["sentiment_score"] >= recs[1]["sentiment_score"]

    def test_derived_cache_is_stored_after_miss(self) -> None:
        """파생 캐시 미스 후 결과를 캐시에 저장한다."""
        client, mock_cache = _make_client_with_cache(_sample_recommendations())

        client.get("/recommendations?limit=3")

        mock_cache.set_derived.assert_called_once()
