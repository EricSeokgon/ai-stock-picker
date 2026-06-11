---
name: project-stock007-search-feedback
description: SPEC-STOCK-007 종목 검색/주가 히스토리/피드백 API 구현 완료. TASK-001~010. 47개 신규 테스트, 전체 458/458.
metadata:
  type: project
---

SPEC-STOCK-007 (종목 검색 + 주가 히스토리 + 피드백) TASK-001~010 완료.

**Why:** 프론트엔드 검색, 차트, 피드백 기능을 위한 백엔드 API 구현.

**How to apply:** 이 SPEC 이후 추가 기능 구현 시 아래 아키텍처 패턴을 유지.

## 구현 파일 목록

### 신규 모델/마이그레이션
- `backend/src/stock_picker/db/models.py` — `RecommendationFeedback` 추가 (vote: "up"/"down", user_id nullable)
- `backend/alembic/versions/0010_recommendation_feedback.py` — revision 0009→0010

### 신규 서비스
- `backend/src/stock_picker/search/service.py` — `search_stocks()`: KRX 마스터 CSV 기반 검색, 최근 7일 추천 여부 표시
- `backend/src/stock_picker/feedback/service.py` — `save_feedback()` / `get_feedback_summary()`
- `backend/src/stock_picker/mapping/prices.py` — `get_stock_price_history()` 추가 (Redis TTL 3600s, graceful fallback)

### 신규 라우터
- `backend/src/stock_picker/api/routes/stocks.py` — `GET /stocks/search`, `GET /stocks/{krx_code}/prices`
- `backend/src/stock_picker/api/routes/recommendations.py` — `POST /{krx_code}/feedback`, `GET /{krx_code}/feedback` 추가

### 신규 스키마
- `backend/src/stock_picker/api/schemas.py` — `StockSearchItem`, `StockSearchResponse`, `PricePoint`, `StockPricesResponse`, `FeedbackVoteRequest`, `FeedbackSummaryResponse` 추가

## 핵심 설계 결정

1. **Redis 장애 대응**: 모든 Redis 연산은 try/except로 래핑 → 실패 시 FDR로 폴백, 그것도 실패 시 `[]` 반환
2. **FDR 비동기 래핑**: `asyncio.get_event_loop().run_in_executor()` 사용 (동기 라이브러리)
3. **피드백 경로 충돌 방지**: `/{krx_code}/feedback` 엔드포인트를 `/{krx_code}` 보다 먼저 등록
4. **선택적 인증**: `HTTPBearer(auto_error=False)` → 토큰 없어도 피드백 허용, user_id=None으로 저장
5. **vote 검증**: 서비스 레이어에서 `ValueError` 발생 → 라우터에서 422로 변환

## 테스트 구조 (47개 신규)
- `tests/unit/test_search_service.py` — 9개
- `tests/unit/test_prices_history.py` — 8개
- `tests/unit/test_feedback_service.py` — 9개
- `tests/integration/test_stocks_router.py` — 15개
- `tests/integration/test_feedback_router.py` — 6개

## mock 패턴 교훈

**중요**: `AsyncMock` 세션에서 `result.all()`은 동기 메서드이므로 `MagicMock(return_value=rows)`로 명시 설정 필요:
```python
mock_result = MagicMock()
mock_result.all = MagicMock(return_value=rows)  # NOT AsyncMock
db.execute.return_value = mock_result
```

**패치 경로**: 라우터에서 임포트된 심볼은 라우터 네임스페이스에서 패치:
- `stock_picker.api.routes.recommendations.save_feedback` (NOT `stock_picker.feedback.service.save_feedback`)
- `stock_picker.api.routes.stocks.get_stock_price_history` (NOT `stock_picker.mapping.prices.get_stock_price_history`)
