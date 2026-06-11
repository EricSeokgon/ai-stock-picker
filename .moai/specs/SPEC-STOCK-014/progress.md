# Progress — SPEC-STOCK-014 AI 투자 조언 고도화 (Phase 15)

- **상태**: COMPLETED
- **생성**: 2026-06-11
- **갱신**: 2026-06-11
- **작성자**: ircp

---

## 현재 단계

| 단계 | 상태 |
|------|------|
| Plan (기획) | 완료 |
| Run (구현) | 완료 |
| Sync (문서화) | 완료 |

---

## 마일스톤 진행

| 마일스톤 | 설명 | 상태 |
|----------|------|------|
| M1 | DB 모델 & 마이그레이션 0015 (`ai_advice` 테이블, down_revision=0014) | DONE |
| M2 | 리밸런싱 제안 API (`POST /advice/rebalance`, REQ-RB-*) | DONE |
| M3 | 리스크 프로파일 분석 (`POST /advice/risk-profile`, REQ-RM-*) | DONE |
| M4 | 맞춤형 시장 브리핑 (`GET /advice/market-briefing`, 1일 1회 캐시, REQ-MB-*) | DONE |
| M5 | 조언 이력 & 품질 피드백 (`GET /advice/history`, `POST /advice/{id}/feedback`, REQ-AIV/FB-*) | DONE |
| M6 | 프론트엔드 UI (포트폴리오 조언 패널·이력·피드백, REQ-FE-*) | DONE |
| M7 | 테스트 & 품질 게이트 (커버리지 85%+, REQ-NFR-*) | DONE |

---

## 구현 결과 요약

### 백엔드 (Python/FastAPI)

- `backend/src/stock_picker/advice/__init__.py` — 패키지 초기화
- `backend/src/stock_picker/advice/service.py` — Claude haiku-4-5 호출 로직, _DISCLAIMER, 예외 격리
- `backend/src/stock_picker/advice/router.py` — 5개 엔드포인트 (`/advice` 프리픽스)
- `backend/src/stock_picker/db/models.py` — AIAdvice 모델 추가 (UNIQUE 제약 포함)
- `backend/alembic/versions/0015_ai_advice.py` — `ai_advice` 테이블 마이그레이션

### 프론트엔드 (React/TypeScript)

- `frontend/src/api/advice.ts` — API 래퍼 (5개 엔드포인트 함수)
- `frontend/src/pages/AdviceHistory.tsx` — 조언 이력 + 피드백 UI
- `frontend/src/pages/Portfolio.tsx` — AdviceSection 컴포넌트 추가 (3탭: 리밸런싱/리스크/시장 브리핑)
- `frontend/src/App.tsx` — `/advice/history` 라우트 및 네비게이션 추가

### 테스트 결과

- 백엔드 단위 테스트: `test_ai_advice_model.py` (19개), `test_advice_service.py` (18개)
- 백엔드 통합 테스트: `test_advice_router.py` (10개)
- 커버리지: `stock_picker.advice` 87.30% (목표 85% 초과)
  - `__init__.py`: 100%, `router.py`: 84%, `service.py`: 93%
- 프론트엔드 테스트: 170개 전체 통과

---

## 핵심 설계 결정 (Plan 단계 확정)

1. **신규 테이블은 `ai_advice` 단일** (마이그 0015). 조언 레코드 + 피드백을 한 테이블에 영속화.
   기존 테이블 컬럼 추가·변경 없음.
2. **신규 라우터 prefix = `/advice`** — 기존 `/notifications` 충돌 사례를 피하기 위해 분리.
3. **모든 조언 Claude 호출은 `claude-haiku-4-5` + 동기 `anthropic.Anthropic`** — 기존
   `portfolio/ai_analysis.py`·`recommendation/explanation.py` 패턴 재사용.
4. **캐싱·멱등성**: `UNIQUE(user_id, advice_type, ref_date)`로 동일 기준일 조언 1회만 생성.
   시장 브리핑은 사용자당 1일 1회 (Redis 키 `ai_advice:briefing:{user_id}:{date}`).
5. **예외 격리**: Claude 실패 시 오류 딕셔너리/폴백 메시지 반환, 예외 비전파 (기존 패턴).
6. **면책 문구 필수** — 모든 조언에 "투자 권유 아님" 명시.
7. **기존 `POST /portfolios/{id}/ai-analysis` 유지** — 신규 엔드포인트만 추가.
8. **자동 매매·실시간·신규 데이터 소스·ML 재가중 영구/범위 제외** (§7).
9. **시장 데이터**: `NewsSentiment` 대신 `AnalysisResult` 모델 사용 (실제 존재하는 테이블).
10. **Redis 선택적 임포트**: `ImportError` 방지를 위해 try/except 패턴 적용.

---

## 이터레이션 로그

### 이터레이션 1 (M1-M2)
- 완료 기준 달성 수: 2/7
- 오류 델타: 0 (신규 오류 없음)
- 신규 생성: `ai_advice` 테이블 마이그레이션, AIAdvice 모델, advice 서비스 모듈

### 이터레이션 2 (M3-M5 + 라우터)
- 완료 기준 달성 수: 5/7
- 오류 델타: -1 (NewsSentiment→AnalysisResult 수정으로 ImportError 해결)
- 신규 생성: advice 라우터 (5개 엔드포인트), 10개 통합 테스트 GREEN

### 이터레이션 3 (M6-M7)
- 완료 기준 달성 수: 7/7
- 오류 델타: 0
- 신규 생성: 프론트엔드 advice.ts, AdviceHistory.tsx, Portfolio.tsx 수정, App.tsx 수정
- 커버리지: 87.30% (목표 초과)

---

## 기존 자산 재사용 요약

- `WatchlistItem`·`PortfolioHolding`·`Recommendation`·`AnalysisResult` 모델 (조회만)
- `analyze_portfolio()` Claude 호출·면책·예외 격리 패턴
- `recommendation/explanation.py` 실패 시 None·예외 격리 패턴
- `get_current_user`·`get_db_session`·`get_redis_client`/`get_cache` 의존성

---

## 다음 액션

SPEC-STOCK-014 완료. 다음 SPEC 계획 시 `/moai plan` 사용.
