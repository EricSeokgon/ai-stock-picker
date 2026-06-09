# Task Decomposition
SPEC: SPEC-STOCK-005

## 마일스톤

- **Phase A** (TASK-001~004): Redis 캐싱 레이어(추천 결과·현재가) — Priority High
- **Phase B** (TASK-005~008): 추천 필터·정렬 API + 프론트 필터 바 — Priority High
- **Phase C** (TASK-009~010): 모바일 반응형 레이아웃 — Priority Medium

## 설계 확정값
- 추천 캐시 키: 기준 `recommendations:{date}`(기존, 불변), 파생 `recommendations:top:{limit}`·`recommendations:sector:{sector}` (TTL 1800s)
- 현재가 캐시 키: `price:{krx_code}` (TTL 60s), 동기 Redis 클라이언트로 `get_current_price`에 레이어 추가
- Redis 접속: 환경 변수 `REDIS_URL`(기본 `redis://localhost:6379/0`), `config.py`/`api/deps.py` 재사용
- [HARD] Redis 미가용/실패 시 캐시 우회 폴백 — 기존 기능 무중단(REQ-CACHE-007, REQ-NFR-002)
- 필터/정렬 파라미터: `limit`(int>0), `sector`(str), `sort` ∈ {score, sentiment, volume}(기본 score), `min_score`(float>=0) — 모두 선택, 전무 시 SPEC-001 동일 응답
- 섹터 파생: 방안 A(권장) 추천 적재 시 `AnalysisResult.sector_tags`에서 대표 섹터 파생→캐시 JSON 포함 (run 단계 확정, DB 스키마 불변)
- 반응형 기준점: <768px 모바일, CSS 미디어 쿼리만 사용(신규 UI 의존성 0)
- 신규 DB 테이블·마이그레이션 없음, 자동 매매 영구 제외

## 의존성
- Phase A는 기존 `recommendation/cache.py`·`api/deps.py`·`realtime/price_feed.py`·`scheduler/jobs.py`에 의존, 먼저 또는 Phase B와 함께 구현
- Phase B는 Phase A 캐시 키 구성·섹터 파생(§5.5)에 의존, 프론트 필터 바는 API 계약 확정 후
- Phase C는 독립적이나 Dashboard 프론트 변경이 필터 바(TASK-008)와 겹치므로 순서 조정

| ID | 설명 | Feature | 주요 파일 | 상태 |
|----|------|---------|----------|------|
| TASK-001 | RecommendationCache 일반화: 파생 키 get/set·`invalidate_derived()`·손상 데이터 미스 처리, 기존 `recommendations:{date}` 동작 보존 | Redis 캐싱 | recommendation/cache.py | done |
| TASK-002 | 현재가 Redis 캐시 레이어: `price:{krx_code}` TTL 60s, 동기 Redis 클라이언트, 미스 시 FinanceDataReader 조회·적재, 실패 시 폴백 | Redis 캐싱 | realtime/price_feed.py | done |
| TASK-003 | 스케줄러 기준 추천 갱신 직후 파생 키(`recommendations:top:*`·`recommendations:sector:*`) 무효화 + 섹터 파생 적재(방안 A) | Redis 캐싱 | scheduler/jobs.py, recommendation/cache.py | done |
| TASK-004 | [HARD] Redis 미가용/손상 폴백 테스트·캐시 히트/미스·무효화 구조화 로그(시크릿 제외) | Redis 캐싱 | recommendation/cache.py, realtime/price_feed.py | done |
| TASK-005 | `GET /recommendations` 쿼리 파라미터 추가(limit/sector/sort/min_score), 캐시 키 구성→조회→미스 시 기준 추천 가공·적재→반환 | 필터·정렬 | api/routes/recommendations.py | done |
| TASK-006 | 필터·정렬 로직: sort 내림차순(score/sentiment/volume), sector 필터, min_score 필터, 조합 적용, 기본 호출 하위 호환 | 필터·정렬 | api/routes/recommendations.py, recommendation/cache.py | done |
| TASK-007 | 파라미터 유효성: sort 허용값 외·음수 limit/min_score 422 또는 기본값 처리(500 금지), 빈 결과 정상 응답 | 필터·정렬 | api/routes/recommendations.py, api/schemas.py | done |
| TASK-008 | 프론트: RecommendationFilterBar(섹터 드롭다운 동적 구성·정렬 select·최소 점수·초기화) + Dashboard 필터 상태·재조회·실패 시 상태 유지 + API 클라이언트 쿼리 전달 | Frontend | components/RecommendationFilterBar.tsx, App.tsx, frontend API 클라이언트 | done |
| TASK-009 | 반응형 CSS: NavBar 햄버거(<768px) + 추천 목록 카드 레이아웃 + 미디어 쿼리만 사용 | Frontend | App.tsx, components/RecommendationList.tsx, CSS | done |
| TASK-010 | 반응형 CSS: 포트폴리오 표(가로 스크롤/카드) + 관심 목록 컴팩트 카드 + >=768px 데스크톱 동작 불변 검증 | Frontend | pages/Portfolio.tsx, pages/Watchlist.tsx, CSS | done |
