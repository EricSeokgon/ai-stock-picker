# ETF 추천기 - 섹터 트렌드 스코어 기반 (REQ-REC-003)
# ETF가 추종하는 섹터들의 trend_score 평균으로 etf_score를 산출한다.
from pathlib import Path
from typing import Any

import structlog

from ..mapping.etf_master import load_etf_master

log = structlog.get_logger()


class EtfRecommender:
    """섹터 트렌드 기반 ETF 추천기.

    # @MX:ANCHOR: [AUTO] ETF 추천기 - RecommendationService에서 호출
    # @MX:REASON: 주식 추천 파이프라인의 ETF 구성 요소 (REQ-REC-003)

    ETF가 커버하는 섹터들의 트렌드 스코어 평균을 etf_score로 산출하고
    내림차순으로 정렬하여 반환한다.
    """

    def __init__(self, etf_master_path: Path | None = None) -> None:
        self._etfs = load_etf_master(etf_master_path)

    def recommend(
        self,
        sector_trends: dict[str, float],
    ) -> list[dict[str, Any]]:
        """섹터 트렌드 스코어를 기반으로 ETF를 추천.

        Args:
            sector_trends: 섹터명 → 트렌드 스코어(0.0~1.0) 딕셔너리

        Returns:
            ETF 추천 목록 (etf_score 내림차순 정렬):
            [{etf_code, etf_name, sectors, etf_score}, ...]
        """
        results: list[dict[str, Any]] = []

        for etf in self._etfs:
            etf_code: str = etf["etf_code"]
            etf_name: str = etf["etf_name"]
            sectors: list[str] = etf["sectors"]

            # 매핑된 섹터의 트렌드 스코어 평균
            matched_scores = [
                sector_trends[s] for s in sectors if s in sector_trends
            ]
            etf_score = sum(matched_scores) / len(matched_scores) if matched_scores else 0.0

            results.append(
                {
                    "etf_code": etf_code,
                    "etf_name": etf_name,
                    "sectors": sectors,
                    "etf_score": etf_score,
                }
            )

        # etf_score 내림차순 정렬
        results.sort(key=lambda x: x["etf_score"], reverse=True)

        log.debug("ETF 추천 완료", count=len(results))
        return results
