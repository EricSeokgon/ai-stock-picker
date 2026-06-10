# SPEC-STOCK-008 작업 분해 (Tasks)

섹터 분석 대시보드 — 섹터 집계 생산자 + 순위/상세 API + 비교 화면.
모든 작업은 기존 스택 재사용·하위 호환·테스트 커버리지 85% 이상을 전제로 한다.

우선순위 표기: Priority High / Medium / Low.

---

## 백엔드 — 섹터 집계 생산자

### TASK-001: `(sector, trade_date)` UNIQUE 제약 마이그레이션 (0011) [Priority High]
- `sector_trends` 테이블에 `(sector, trade_date)` 복합 UNIQUE 제약을 추가하는 Alembic
  마이그레이션 `0011` 작성(누적: 0010 다음).
- upsert(REQ-SEC-003)의 멱등성 보장을 위한 사전 작업.
- 관련: REQ-SEC-003
- 의존: 없음

### TASK-002: 섹터 집계 서비스 구현 [Priority High]
- 신규 모듈(`sector/` 또는 `recommendation/` 내)에 거래일 단위 섹터 집계 함수 구현.
- 입력: 해당 거래일의 `AnalysisResult`(`sector_tags`, `sentiment_score`, 기사 연결).
- 출력: 섹터별 `news_volume`, `avg_sentiment`, `trend_score` 산출.
- `trend_score`는 평균 감성과 뉴스 볼륨을 결합한 파생식(구현 단계에서 가중치 확정).
- 기사가 여러 섹터 태그를 가질 경우 각 섹터에 카운트(다중 태깅 허용).
- 관련: REQ-SEC-001, REQ-SEC-002, REQ-NFR-004
- 의존: 없음

### TASK-003: 섹터 집계 upsert 저장 [Priority High]
- 집계 결과를 `sector_trends`에 저장하되, 동일 `(sector, trade_date)` 존재 시 갱신(upsert).
- 빈 분석 결과(기사 0건) 시 행을 생성하지 않음.
- 관련: REQ-SEC-003, REQ-SEC-004
- 의존: TASK-001, TASK-002

### TASK-004: 파이프라인 연결 + 캐시 무효화 [Priority High]
- `run_daily_pipeline`·`run_intraday_pipeline`에 섹터 집계 단계를 분석 단계 이후·추천 단계
  전후로 삽입.
- 집계 단계 예외 시 로깅 후 추천 단계 계속 진행(파이프라인 비중단).
- 집계 완료 후 `sector_trends:{days}` Redis 캐시 무효화.
- 관련: REQ-SEC-001, REQ-SEC-005, REQ-SEC-006
- 의존: TASK-003

---

## 백엔드 — 섹터 순위/상세 API

### TASK-005: 섹터 순위 API (`GET /sectors/ranking`) [Priority High]
- 최신 거래일 기준 섹터 정렬 목록 반환. `sort=score|sentiment|volume`, `limit` 지원.
- 캐시 우선 패턴(`sectors.py` 기존 방식) 준수.
- 응답 스키마(`SectorRankingResponse`/`SectorRankingItem`) 추가.
- 관련: REQ-SEC-010, REQ-SEC-011, REQ-SEC-014
- 의존: TASK-003

### TASK-006: 섹터 상세 API (`GET /sectors/{sector}/detail`) [Priority High]
- 해당 섹터의 최근 N일 트렌드 시계열 + 구성 종목 목록(종목코드·언급 횟수) 반환.
- 구성 종목은 `StockMention` → `Article` → `AnalysisResult`(sector_tags 포함) 조인으로 파생.
- 존재하지 않는 섹터는 404 + 한국어 메시지.
- 응답 스키마(`SectorDetailResponse` 등) 추가.
- 관련: REQ-SEC-012, REQ-SEC-013
- 의존: TASK-003

### TASK-007: 백엔드 단위·통합 테스트 [Priority High]
- 집계 서비스 단위 테스트(다중 섹터 태깅, 빈 결과, upsert 멱등성, trend_score 계산).
- API 통합 테스트(`/sectors/ranking` 정렬·limit, `/sectors/{sector}/detail` 정상·404,
  캐시 히트 경로, 파이프라인 집계 후 `/sectors/trends` 비어있지 않음).
- 커버리지 85% 이상 확인.
- 관련: REQ-NFR-003, 전체 REQ-SEC-*
- 의존: TASK-004, TASK-005, TASK-006

---

## 프론트엔드 — 섹터 비교 화면

### TASK-008: 섹터 API 클라이언트 + 타입 [Priority Medium]
- `api/client.ts`에 `fetchSectorRanking`, `fetchSectorDetail` 추가.
- `types.ts`에 `SectorRankingItem`, `SectorDetailResponse` 등 타입 추가.
- 관련: REQ-SECUI-001, REQ-SECUI-002
- 의존: TASK-005, TASK-006

### TASK-009: `/sectors` 페이지 — 순위 표 + 비교 차트 [Priority Medium]
- 섹터 순위 표(정렬 전환 가능)와 섹터 트렌드 비교 차트(Recharts) 렌더.
- 데이터 미적재 시 "섹터 데이터 준비 중" 안내 상태 표시.
- 관련: REQ-SECUI-001, REQ-SECUI-003
- 의존: TASK-008

### TASK-010: 섹터 상세 패널 (구성 종목 + 추세) [Priority Medium]
- 순위 표에서 섹터 선택 시 상세(추세 시계열 + 구성 종목 목록) 표시.
- 구성 종목 클릭 시 기존 종목 상세(`StockDetail`/`/stocks/:krxCode`)와 연계 가능하면 연결.
- 관련: REQ-SECUI-002
- 의존: TASK-009

### TASK-011: 라우팅 + NavBar 링크 + 반응형 [Priority Medium]
- `App.tsx`에 `/sectors` 라우트 추가, NavBar에 "섹터 분석" 링크 추가(공개 라우트).
- 768px 미만 반응형 동작 유지(기존 햄버거 메뉴 패턴 준수).
- 관련: REQ-SECUI-004
- 의존: TASK-009

### TASK-012: 프론트엔드 테스트 + 문서 갱신 [Priority Low]
- `/sectors` 페이지·상세 패널 컴포넌트 테스트(데이터 있음/없음/오류).
- README 섹터 분석 기능 설명 추가, CHANGELOG 항목 추가.
- 관련: REQ-NFR-001, REQ-SECUI-003
- 의존: TASK-009, TASK-010, TASK-011
