---
name: project-stock009-feedback-weighting
description: SPEC-STOCK-009 피드백 기반 가중치 + 점수 투명성 구현 완료. 신뢰도 가중 피드백 계수, 벌크 조회, score_breakdown API. 테스트 516/516.
metadata:
  type: project
---

SPEC-STOCK-009 TASK-001~009 완료. 피드백 기반 가중치 조정 + 점수 투명성 기능 구현.

**구현 파일:**
- `alembic/versions/0012_recommendation_feedback_score.py` — base_score, feedback_score 컬럼 추가
- `src/stock_picker/db/models.py` — Recommendation 모델에 base_score, feedback_score nullable 컬럼 추가
- `src/stock_picker/feedback/weighting.py` (신규) — calculate_feedback_coefficient, apply_feedback_adjustment 순수 함수
- `src/stock_picker/feedback/service.py` — get_bulk_feedback() 추가 (N+1 방지 GROUP BY 단일 쿼리)
- `src/stock_picker/recommendation/service.py` — run()에 피드백 조정 통합 (벌크 조회 후 일괄 적용)
- `src/stock_picker/scoring/engine.py` — decompose_score() 추가 (기존 함수 미수정)
- `src/stock_picker/api/schemas.py` — ScoreFactorContribution, ScoreBreakdown 신규, RecommendationItem/DetailResponse 확장
- `src/stock_picker/api/routes/recommendations.py` — 상세 API에 score_breakdown 포함

**테스트:**
- `tests/unit/test_feedback_weighting.py` (신규, 10개)
- `tests/unit/test_score_adjustment.py` (신규, 14개)
- `tests/integration/test_recommendation_feedback_weighting.py` (신규, 11개)
- `tests/integration/test_recommendation.py` — 기존 3개 테스트에 get_bulk_feedback patch 추가 (기존 4개 실패 수정)

**Why:** 기존 테스트들이 mock_session = AsyncMock()으로 설정되어 있어, get_bulk_feedback가 execute를 호출하면 .all()이 코루틴을 반환하는 문제 발생. recommendation/service.py에서 get_bulk_feedback를 import하므로 patch 경로는 "stock_picker.recommendation.service.get_bulk_feedback".

**전체 테스트 결과:** 516/516 passed (이전 481→516, 신규 35개)

**HARD CONSTRAINTS 준수:**
- calculate_stock_score(), rank_stocks() 미수정 (REQ-NFR-001)
- 모든 신규 recommendations 컬럼 nullable
- MAX_ADJ=0.15, MIN_VOTES_FOR_CONFIDENCE=5
