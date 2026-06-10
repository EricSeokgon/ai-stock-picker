# 추천 서비스 - 집계 + 스코어링 + 저장 + 캐시
# AC-5: total_score = 0.40*sentiment + 0.20*volume + 0.25*momentum + 0.15*anomaly
from datetime import date, datetime, timezone
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Recommendation
from ..feedback.service import get_bulk_feedback
from ..feedback.weighting import apply_feedback_adjustment, calculate_feedback_coefficient
from ..mapping.prices import get_stock_price_data
from ..scoring.engine import calculate_stock_score, rank_stocks
from ..scoring.reasoning import generate_reasoning
from .aggregator import StockAggregator
from .cache import RecommendationCache
from .explanation import generate_explanation

log = structlog.get_logger()

# Redis 캐시 키 형식
_CACHE_KEY_FORMAT = "recommendations:{date}"


class RecommendationService:
    """추천 파이프라인 서비스.

    # @MX:ANCHOR: [AUTO] 추천 파이프라인 최상위 진입점 - API 라우터와 스케줄러에서 호출
    # @MX:REASON: FastAPI 라우터, APScheduler에서 호출되는 핵심 서비스

    실행 순서:
    1. Redis 캐시 조회 (히트 시 바로 반환)
    2. 종목별 뉴스 집계
    3. 시세 조회
    4. 스코어 계산
    5. Top 10 저장
    6. Redis 캐시 갱신
    """

    def __init__(self, cache: RecommendationCache | None = None) -> None:
        self._aggregator = StockAggregator()
        self._cache = cache

    async def run(
        self,
        session: AsyncSession,
        trade_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """추천 파이프라인 실행.

        Args:
            session: 비동기 DB 세션
            trade_date: 추천 기준 날짜. None이면 오늘.

        Returns:
            상위 10개 추천 딕셔너리 목록.
        """
        today = trade_date or date.today()
        cache_key = _CACHE_KEY_FORMAT.format(date=today.isoformat())

        # 1단계: 캐시 조회
        if self._cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                log.info("캐시 히트", cache_key=cache_key)
                return cached

        # 2단계: 종목별 뉴스 집계
        aggregated = await self._aggregator.aggregate(session, today)

        if not aggregated:
            log.warning("집계된 종목 없음", trade_date=today)
            return []

        # 3단계: 시세 조회 및 스코어 계산
        scores: dict[str, float] = {}
        stock_details: dict[str, dict[str, Any]] = {}

        for krx_code, agg_data in aggregated.items():
            price_data = await get_stock_price_data(krx_code)

            # 감성 점수 정규화 (-1~1 → 0~1)
            raw_sentiment = agg_data["avg_sentiment"]
            sentiment_normalized = (raw_sentiment + 1.0) / 2.0

            # 뉴스 볼륨 점수 (단순화: 뉴스 수를 정규화)
            news_count = agg_data["news_count"]
            volume_score = min(news_count / 10.0, 1.0)  # 10개 이상이면 1.0

            # 모멘텀 및 이상거래 점수 (시세 데이터 기반)
            momentum_score = 0.0
            anomaly_score = 0.0

            if price_data:
                change_rate = price_data.get("change_rate", 0.0)
                # 변화율을 0~1로 정규화 (±10% 범위 기준)
                momentum_score = max(0.0, min(1.0, (change_rate + 0.1) / 0.2))
                # 거래량 기반 이상거래 점수 (단순화)
                vol = price_data.get("volume", 0)
                anomaly_score = min(vol / 20_000_000, 1.0)  # 2천만주 기준

            total_score = calculate_stock_score(
                sentiment_normalized,
                volume_score,
                momentum_score,
                anomaly_score,
            )

            scores[krx_code] = total_score
            stock_details[krx_code] = {
                "sentiment_score": sentiment_normalized,
                "volume_score": volume_score,
                "momentum_score": momentum_score,
                "anomaly_score": anomaly_score,
                "top_summary": agg_data.get("top_summary", ""),
            }

        # 4단계: 피드백 가중치 조정 (벌크 조회 — N+1 쿼리 방지)
        bulk_feedback = await get_bulk_feedback(session, list(scores.keys()))
        for krx_code_fb, base in list(scores.items()):
            fb = bulk_feedback.get(krx_code_fb, {"up": 0, "down": 0})
            coeff = calculate_feedback_coefficient(fb["up"], fb["down"])
            adjusted, fb_score = apply_feedback_adjustment(base, coeff)
            scores[krx_code_fb] = adjusted
            stock_details[krx_code_fb]["base_score"] = base
            stock_details[krx_code_fb]["feedback_score"] = fb_score

        # 5단계: Top 10 순위화
        ranked = rank_stocks(scores, top_n=10)

        # 6단계: 결과 구성
        recommendations: list[dict[str, Any]] = []
        for rank, (krx_code, total_score) in enumerate(ranked, start=1):
            detail = stock_details[krx_code]
            reasoning = generate_reasoning(
                krx_code=krx_code,
                sentiment_score=detail["sentiment_score"],
                volume_score=detail["volume_score"],
                momentum_score=detail["momentum_score"],
                anomaly_score=detail["anomaly_score"],
                top_article_summary=detail.get("top_summary"),
            )

            # 설명 생성 (실패해도 파이프라인 중단 없음 — TASK-003)
            score_breakdown = {
                "sentiment_score": detail["sentiment_score"],
                "volume_score": detail["volume_score"],
                "momentum_score": detail["momentum_score"],
                "anomaly_score": detail["anomaly_score"],
            }
            explanation = await generate_explanation(
                krx_code=krx_code,
                score_breakdown=score_breakdown,
                top_summary=detail.get("top_summary", ""),
            )
            if explanation is not None:
                log.info("설명 생성 완료 — krx_code=%s", krx_code)
            else:
                # 폴백: reasoning 텍스트를 explanation으로 사용
                explanation = reasoning
                log.warning("설명 생성 실패, 폴백 적용 — krx_code=%s", krx_code)

            rec = {
                "rank": rank,
                "krx_code": krx_code,
                "total_score": round(total_score, 3),
                "base_score": round(detail.get("base_score", total_score), 3),
                "feedback_score": round(detail.get("feedback_score", 0.0), 3),
                "sentiment_score": round(detail["sentiment_score"], 3),
                "volume_score": round(detail["volume_score"], 3),
                "momentum_score": round(detail["momentum_score"], 3),
                "anomaly_score": round(detail["anomaly_score"], 3),
                "reasoning": reasoning,
                "explanation": explanation,
                "trade_date": today.isoformat(),
            }
            recommendations.append(rec)

        # 7단계: DB 저장
        await self._save_recommendations(session, recommendations, today)

        # 8단계: 캐시 갱신
        if self._cache:
            await self._cache.set(cache_key, recommendations)

        return recommendations

    async def _save_recommendations(
        self,
        session: AsyncSession,
        recommendations: list[dict[str, Any]],
        trade_date: date,
    ) -> None:
        """추천 결과를 DB에 저장.

        Args:
            session: 비동기 DB 세션
            recommendations: 추천 목록
            trade_date: 거래 날짜
        """
        trade_dt = datetime.combine(trade_date, datetime.min.time(), tzinfo=timezone.utc)

        for rec in recommendations:
            db_rec = Recommendation(
                trade_date=trade_dt,
                asset_type="stock",
                krx_code=rec["krx_code"],
                rank=rec["rank"],
                total_score=rec["total_score"],
                base_score=rec.get("base_score"),
                feedback_score=rec.get("feedback_score"),
                sentiment_score=rec["sentiment_score"],
                volume_score=rec["volume_score"],
                momentum_score=rec["momentum_score"],
                anomaly_score=rec["anomaly_score"],
                reasoning=rec.get("reasoning"),
                explanation=rec.get("explanation"),
            )
            session.add(db_rec)

        await session.flush()
