---
name: project-stock006-explanation
description: SPEC-STOCK-006 TASK-001~009, TASK-011 백엔드 구현 완료. Claude 추천 근거 생성, 히스토리 API, 감성 라벨.
metadata:
  type: project
---

SPEC-STOCK-006 백엔드 태스크 구현 완료 (2026-06-10).

**Why:** 추천 결과에 AI 생성 한국어 근거 텍스트, 히스토리 API, 감성 5단계 라벨 기능 추가.

**How to apply:** 이후 동일 SPEC 작업 시 아래 파일 위치 참조.

## 구현된 파일

- `alembic/versions/0009_explanation_sentiment_label.py` — recommendations.explanation, analysis_results.sentiment_label 컬럼 추가
- `db/models.py` — Recommendation.explanation, AnalysisResult.sentiment_label 필드 추가
- `recommendation/explanation.py` — generate_explanation() Claude Haiku 추천 근거 생성
- `analysis/sentiment_label.py` — score_to_label() 5단계 라벨 변환
- `recommendation/service.py` — 파이프라인에 explanation 생성 통합
- `api/schemas.py` — RecommendationItem.explanation, NewsItem.sentiment_label, RecommendationHistoryResponse 추가
- `api/routes/recommendations.py` — GET /recommendations/history 추가 (/{krx_code} 이전 등록 필수)
- `api/routes/news.py` — sentiment_label 필드 포함

## 테스트 결과

- `tests/unit/test_explanation.py` — 7/7 통과
- `tests/unit/test_sentiment_label.py` — 28/28 통과
- `tests/integration/test_recommendation_history.py` — 9/9 통과
- 전체 단위 테스트 283/283 통과 (회귀 없음)

## 중요 패턴

- Mock 속성 MagicMock 문제: `rec.explanation`처럼 직접 접근 시 MagicMock이 반환됨. `isinstance(_raw, str)` 체크 필수.
- /recommendations/history 라우트는 /{krx_code} 보다 먼저 등록해야 경로 충돌 없음.
- generate_explanation 실패 시 reasoning 텍스트를 폴백으로 사용 — 파이프라인 절대 중단 금지.
