# SPEC-STOCK-039 — 구현 계획 (Plan)

시간 추정은 사용하지 않는다. 우선순위(High/Medium/Low)와 단계 순서로 기술한다.

## 기술 접근

### 백엔드

1. **장중 판정 순수 함수** (`portfolio/` 패키지 신규 모듈, 예: `portfolio/market_status.py`)
   - `is_market_open(now_kst: datetime | None = None) -> bool`: 평일(월–금) AND `time(9,0) <= now.time() <= time(15,30)` 검사. `ZoneInfo("Asia/Seoul")` 사용. 표준 라이브러리만(NFR-002, NFR-005).
   - 기존 `general_alert_service._is_market_open`은 요일 미검사 + SPEC-023 소유 → **수정하지 않고 별도 신설**(스코프 규율).
   - `@MX:ANCHOR` + `@MX:REASON`(서비스·라우터·테스트 fan_in≥3), `@MX:NOTE`(SPEC-023과 별개·평일 검사 추가).
   - 시장 상태 응답 빌더 함수: `{"is_open": bool, "now_kst": iso, "session": "open"|"closed"}` 형태(스키마는 schemas.py에 `MarketStatus` 추가).

2. **시장 상태 엔드포인트** (public)
   - `GET /market/status` — 인증 의존성 없음. `is_market_open()` 호출 결과 반환.
   - `/portfolios` prefix 밖 신규 라우터(`market/router.py`) 또는 기존 시장 메타 라우터에 배치. `@MX:NOTE`로 public 명시.
   - 앱 등록(`main.py` include_router).

3. **현재가 갱신 재사용**
   - 폴링은 기존 `GET /portfolios/{id}/performance`(인증·소유권 404) 재호출. 백엔드 신규 갱신 엔드포인트 없음(REQ-POLL-015, REQ-POLL-060).

### 프론트엔드 (`.js`/`.ts` 쌍 동시 수정)

4. **API 래퍼** (`api/portfolio.ts` + `.js` 또는 신규 `api/market.ts` + `.js`)
   - `apiGetMarketStatus()`: public `GET /market/status` 호출(토큰 불필요).
   - `apiGetPerformance`는 기존 재사용(수정 없음).

5. **폴링 훅** (신규 `hooks/usePricePolling.ts` + `.js` 또는 페이지 내 구현)
   - 주기 선택(30/60/120, 기본 60 — REQ-POLL-011/012).
   - 일시중지/재개 상태(REQ-POLL-013/014).
   - 사이클 시작 전 `apiGetMarketStatus` 확인 → 마감이면 스킵(REQ-POLL-020~022).
   - in-flight 가드: 직전 요청 미완료 시 스킵(NFR-004, REQ-POLL-050).
   - `useEffect` cleanup으로 화면 이탈 시 타이머 해제(REQ-POLL-040).
   - 마지막 갱신 시각 상태(REQ-POLL-032).

6. **상태 배지 컴포넌트** (신규 `components/MarketStatusBadge.js`)
   - 장 중/장 마감 표시(REQ-POLL-030/031) + 마지막 갱신 시각.
   - Portfolio·Dashboard 페이지 통합(`.tsx`/`.js`, `.js` 쌍).

## 작업 분해

### T-001 (High) — 장중 판정 순수 함수
- `portfolio/market_status.py` 신규: `is_market_open(now_kst)` 평일+시간 경계 검사.
- 표준 라이브러리만. `@MX:ANCHOR`/`@MX:NOTE`.
- 단위 테스트: 개장 경계(09:00/15:30)·직전직후(08:59/15:31)·주말·평일 케이스.

### T-002 (High) — 시장 상태 스키마·서비스
- `schemas.py`에 `MarketStatus` 추가(`is_open`, `now_kst`, `session`).
- 상태 빌더 함수 작성(순수 함수 결과 직렬화).

### T-003 (High) — public 시장 상태 엔드포인트
- `GET /market/status` 라우터 신규(인증 없음). 앱 등록.
- 테스트: 미인증 200 응답, 개장/마감 분기(시각 주입 가능 구조 또는 monkeypatch).

### T-004 (High) — 프론트 API 래퍼
- `apiGetMarketStatus` 추가(`.ts`+`.js`). 토큰 불필요.

### T-005 (High) — 폴링 훅
- 주기 선택·기본 60·일시중지/재개·장중 게이팅·in-flight 스킵·cleanup·마지막 갱신 시각.
- `.ts`+`.js` 쌍.

### T-006 (Medium) — 상태 배지 컴포넌트
- 장 중/장 마감 배지 + 마지막 갱신 시각. `.js`.

### T-007 (Medium) — 페이지 통합
- `Portfolio.tsx`/`.js`, `Dashboard.tsx`/`.js`에 폴링 훅·배지·주기 선택 UI 연결.

### T-008 (Medium) — 통합 검증
- 시나리오 1~6 수동/통합 확인. ruff·테스트 커버리지 ≥85%.

## 리스크

| 리스크 | 영향 | 완화 |
|--------|------|------|
| 기존 `_is_market_open`와 혼동 | 중복·드리프트 | 신규 함수 별도 작성, MX:NOTE로 구분 명시, 기존 함수 미수정 |
| 폴링 과다 호출로 쿼터 소진 | 중 | 장중 게이팅 + in-flight 스킵 + 기본 60초 |
| 화면 이탈 후 타이머 누수 | 중 | useEffect cleanup 필수 |
| public 엔드포인트 오용 | 저 | 시장 상태는 비민감 전역 정보만 노출(포트폴리오·사용자 데이터 미포함) |

## 마이그레이션

없음. 신규 테이블·컬럼 없음. 최신 리비전 0024 유지.
