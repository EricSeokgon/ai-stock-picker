# Task Decomposition
SPEC: SPEC-STOCK-006

## 마일스톤

- **Phase A** (TASK-001~004): 추천 근거 설명 — Claude explanation 생성·저장·노출 (Priority High)
- **Phase B** (TASK-005~007): 추천 히스토리 조회 API + 프론트 히스토리 페이지 (Priority High)
- **Phase C** (TASK-008~010): 뉴스 감성 5단계 라벨 — DB·API·프론트 (Priority Medium)

## 설계 확정값
- 신규 마이그레이션 `0009_explanation_sentiment_label`: `recommendations.explanation`(Text, nullable), `analysis_results.sentiment_label`(String(20), nullable). 최신 마이그레이션 = `0008`.
- `explanation`(Claude 자연어, 신규) ↔ `reasoning`(규칙 기반, 보존) 분리. 둘 다 응답 포함.
- 설명 생성: `recommendation/service.py` 추천 적재 직전, 입력 = 점수 분해 + `aggregator` `top_summary`, 모델 `claude-haiku-4-5`, 클라이언트 `anthropic.AsyncAnthropic`.
- [HARD] Claude 설명 실패 시 폴백(explanation 공란 또는 reasoning 대체) — 파이프라인 무중단(REQ-EXPL-005).
- 히스토리: `GET /recommendations/history?days=N`(기본 7, 보정 1~90), DB 직접 조회(`recommendations`), `trade_date` 그룹화·최신 우선, 공개 엔드포인트.
- 감성 5단계 매핑(잠정): >=0.6 매우긍정 / >=0.2 긍정 / >-0.2 중립 / >-0.6 부정 / <=-0.6 매우부정 (run에서 미세 조정).
- 스키마 하위 호환: 신규 필드 Optional(`explanation`, `sentiment_label`), 히스토리 신규 스키마.
- 자동 매매 영구 제외, 면책 고지 유지, 과거 데이터 백필 비필수.

## 의존성
- Phase A·C는 마이그레이션 `0009`(TASK-001)에 선행 의존. TASK-001을 먼저 완료.
- Phase B 히스토리 API(TASK-005)는 `explanation`(TASK-002)이 응답에 포함되도록 TASK-002 이후가 바람직하나, 컬럼만 있으면 독립 진행 가능.
- 프론트(TASK-007·010)는 각 API 계약(TASK-005·009) 확정 후.

| ID | 설명 | Feature | 주요 파일 | 상태 |
|----|------|---------|----------|------|
| TASK-001 | Alembic `0009` 마이그레이션: `recommendations.explanation`(Text, nullable) + `analysis_results.sentiment_label`(String(20), nullable) 추가, ORM 모델 동기화, 다운그레이드 drop | 마이그레이션 | backend/alembic/versions/0009_explanation_sentiment_label.py, db/models.py | pending |
| TASK-002 | Claude 설명 생성기: 점수 분해 + 대표 뉴스 요약 입력→한국어 2~3문장 근거 생성(투자 권유·수익 보장 표현 금지 프롬프트), `claude-haiku-4-5` 재사용 | 추천 근거 설명 | recommendation/explanation.py(신규), analysis/client.py | pending |
| TASK-003 | 추천 파이프라인 통합: 추천 적재 직전 explanation 생성·저장, [HARD] 실패 시 폴백(공란/reasoning)·무중단, 추천당 1회 호출, 구조화 로그(시크릿 제외) | 추천 근거 설명 | recommendation/service.py, recommendation/aggregator.py | pending |
| TASK-004 | 추천 API 응답에 `explanation` 노출: `GET /recommendations`(캐시 JSON 포함)·`GET /recommendations/{krx_code}` 응답 + 스키마 Optional 필드 추가 | 추천 근거 설명 | api/routes/recommendations.py, api/schemas.py | pending |
| TASK-005 | `GET /recommendations/history?days=N` 엔드포인트: DB 조회(최근 N일, 기본 7, 1~90 보정), `trade_date` 그룹화·최신 우선, 빈 기간 `[]`, 잘못된 days 422/보정(500 금지), 공개 접근 | 추천 히스토리 | api/routes/recommendations.py, api/schemas.py | pending |
| TASK-006 | 히스토리 응답 스키마 정의(`RecommendationHistoryResponse`: 날짜별 그룹 → 종목·rank·total_score·explanation) + 단위 테스트(그룹화·정렬·경계값) | 추천 히스토리 | api/schemas.py, tests/unit | pending |
| TASK-007 | 프론트 히스토리 페이지: 날짜별 그룹 표시 + 기간 선택(7/14/30일)→days 반영·재조회 + 실패 시 오류·직전 상태 유지 + 면책 고지 + API 클라이언트 | Frontend | frontend pages/History.tsx(신규), App.tsx, services/api.ts | pending |
| TASK-008 | 감성 5단계 매핑 유틸 + 저장 통합: `sentiment_score`→`sentiment_label` 매핑(경계값), 분석 결과 저장 시 라벨 채움, 점수 null 시 라벨 null(무오류) | 감성 상세화 | analysis/worker.py, analysis/sentiment_label.py(신규) | pending |
| TASK-009 | 뉴스 API 노출: `GET /news` 응답에 `sentiment_label` 포함 + `NewsItem` Optional 필드 추가, 기존 `sentiment` 보존 | 감성 상세화 | api/routes/news.py, api/schemas.py | pending |
| TASK-010 | 프론트 감성 배지: `NewsFeed`에 `sentiment_label`(5단계) 배지 표시, 값 없으면 기존 `sentiment` 배지 유지, 색상/문구 매핑 | Frontend | frontend components/NewsFeed.tsx | pending |
| TASK-011 | 통합 테스트: explanation 생성 폴백·history 엔드포인트(빈/잘못된 days)·sentiment_label 매핑·하위 호환(신규 필드 미사용 클라이언트) | 품질 | tests/integration, tests/unit | pending |
