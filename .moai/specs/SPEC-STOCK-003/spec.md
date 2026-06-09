---
id: SPEC-STOCK-003
version: 0.1.0
status: draft
created: 2026-06-09
updated: 2026-06-09
author: ircp
priority: high
issue_number: null
---

# SPEC-STOCK-003: 한국 주식 & ETF 추천 시스템 — Phase 4 (실시간 시세·관심 목록·포트폴리오 AI 분석)

## HISTORY

- 2026-06-09 (v0.1.0): 최초 작성. SPEC-STOCK-001(MVP)·SPEC-STOCK-002(개인화 기능) 완료 위에 Phase 4 3대 기능(WebSocket 실시간 시세, 종목 관심 목록, 포트폴리오 AI 분석)을 단일 SPEC으로 정의.

---

## 1. 시스템 개요

### 1.1 목적

SPEC-STOCK-001(추천 엔진·대시보드)과 SPEC-STOCK-002(JWT 인증·텔레그램·포트폴리오·백테스팅) 위에, **실시간성·개인화 큐레이션·AI 인사이트** 축으로 시스템을 확장한다. Phase 4는 다음을 더한다.

1. **WebSocket 실시간 시세**: 30분 batch 갱신의 한계를 보완하여 10초 주기 가격 push를 제공.
2. **종목 관심 목록(Watchlist)**: 추천·검색에서 발견한 종목을 사용자별로 저장하고 실시간 시세와 함께 추적.
3. **포트폴리오 AI 분석**: Claude API로 포트폴리오 구성을 분석하여 분산·리스크·개선 제안을 한국어로 제시.

### 1.2 타겟 사용자

| 사용자 그룹 | 특성 | Phase 4에서 추가되는 핵심 니즈 |
|------------|------|------------------------------|
| 액티브 트레이더 | 즉각적인 가격 변동 추적 중시 | 보유·관심 종목의 실시간 시세를 새로고침 없이 확인 |
| 개인 투자자 (입문~중급) | 관심 종목을 흩어진 채로 관리 | 추천 카드에서 별표 한 번으로 관심 목록에 모아 실시간 추적 |
| 검증 지향 사용자 | 본인 포트폴리오 구성의 건전성에 확신이 없음 | 분산도·집중 리스크·개선점을 AI가 한국어로 진단 |

### 1.3 핵심 가치 제안

- **실시간성**: pull(수동 새로고침) 및 batch(30분) 한계를 WebSocket push(10초)로 보완.
- **개인화 큐레이션**: 추천에서 관심 목록으로 이어지는 자연스러운 종목 수집 동선.
- **AI 인사이트**: 단순 수익률 표시를 넘어 구성의 질을 진단하는 분석 레이어.
- **안전한 확장**: 실시간 시세·관심 목록·AI 분석 모두 **정보 제공**에 한정하며, 자동 매매는 영구 제외를 유지.

### 1.4 기존 시스템과의 관계 (SPEC-STOCK-001/002 재정의 금지)

다음은 이미 구현 완료된 자산이며 **본 SPEC에서 재정의하지 않고 재사용**한다.

- 백엔드: FastAPI + PostgreSQL + Redis, 프론트엔드: React 18 + TypeScript + Vite + Recharts + React Router
- 인증: SPEC-STOCK-002의 JWT 인증(`users` 테이블, `get_current_user` 의존성) — Phase B/C가 의존
- 기존 테이블: `users`, `recommendations`, `portfolios`, `portfolio_holdings` 등 (마이그레이션 0001~0005)
- 기존 시세 조회: FinanceDataReader (실시간 시세 폴러·관심 목록 시세에 재사용)
- 기존 추천 API: `GET /recommendations` (관심 목록 별표 토글의 대상 종목)
- 기존 포트폴리오 API: `GET /portfolio`, `GET /portfolio/performance` (AI 분석 입력 데이터원)
- 기존 Claude API 연동: SPEC-STOCK-001의 감성 분석 클라이언트 패턴 (AI 분석에 재사용)

---

## 2. 핵심 기능 요구사항 (EARS)

표기 규칙: **WHEN**(이벤트 구동), **WHILE**(상태 구동), **WHERE**(선택적 기능), **IF...THEN**(원치 않는 동작), **SHALL**(보편 요구).

### 2.1 WebSocket 실시간 시세 (REQ-WS) — Priority High

- **REQ-WS-001 (Event)**: **WHEN** 클라이언트가 `ws://<host>/ws/prices/{krx_code}`로 WebSocket 연결을 수립하면, the 시스템 **SHALL** 연결을 수락하고 즉시 해당 종목의 최신 가격 1건을 전송한다.
- **REQ-WS-002 (State)**: **WHILE** WebSocket 연결이 유지되는 동안, the 시스템 **SHALL** 약 10초 주기로 FinanceDataReader 기준 현재가를 조회하여 가격 갱신 메시지를 전송한다.
- **REQ-WS-003 (Ubiquitous)**: the 시스템 **SHALL** 각 가격 메시지에 `krx_code`, `price`, `change_pct`(전일 종가 대비), `timestamp`(ISO 8601)를 JSON으로 포함한다.
- **REQ-WS-004 (Event)**: **WHEN** 클라이언트가 연결을 종료(closed/disconnect)하면, the 시스템 **SHALL** 해당 연결의 폴링 루프를 정리하여 자원을 회수한다.
- **REQ-WS-005 (Unwanted)**: **IF** 존재하지 않거나 형식이 잘못된 `krx_code`로 연결이 시도되면, **THEN** the 시스템 **SHALL** 오류 메시지를 1회 전송한 뒤 연결을 종료한다.
- **REQ-WS-006 (Unwanted)**: **IF** 특정 주기에 시세 조회가 실패하면, **THEN** the 시스템 **SHALL** 해당 주기를 스킵하고 오류를 로그한 뒤 다음 주기에 재시도하며, 연결은 끊지 않는다.
- **REQ-WS-007 (Ubiquitous)**: the 시스템 **SHALL** 동일 `krx_code`에 대한 다수 동시 연결을 허용하되, 단일 종목당 중복 시세 조회를 최소화하도록 최신 가격을 공유(캐시)한다.

### 2.2 종목 관심 목록 / Watchlist (REQ-WL) — Priority Medium

- **REQ-WL-001 (Event)**: **WHEN** 인증된 사용자가 `GET /watchlist`를 호출하면, the 시스템 **SHALL** 해당 사용자의 관심 종목 목록(krx_code, added_at)을 반환한다.
- **REQ-WL-002 (Event)**: **WHEN** 인증된 사용자가 `POST /watchlist`로 krx_code를 제출하면, the 시스템 **SHALL** 해당 종목을 사용자 관심 목록에 추가하고 `watchlist_items`에 저장한다.
- **REQ-WL-003 (Event)**: **WHEN** 인증된 사용자가 `DELETE /watchlist/{krx_code}`를 호출하면, the 시스템 **SHALL** 해당 종목을 사용자 관심 목록에서 제거한다.
- **REQ-WL-004 (Ubiquitous)**: the 시스템 **SHALL** (user_id, krx_code) 조합에 대해 중복 등록을 방지한다(유니크 제약).
- **REQ-WL-005 (State)**: **WHILE** 사용자가 인증되지 않은 상태에서 관심 목록 엔드포인트에 접근하면, the 시스템 **SHALL** 401을 반환하고 어떤 관심 목록 데이터도 노출하지 않는다.
- **REQ-WL-006 (Unwanted)**: **IF** 이미 등록된 종목의 재등록, 미등록 종목의 삭제, 또는 다른 사용자의 관심 목록 조작이 시도되면, **THEN** the 시스템 **SHALL** 해당 요청을 적절한 상태 코드(409/404/403)로 거부한다.
- **REQ-WL-007 (Event)**: **WHEN** 인증된 사용자가 관심 목록 페이지를 열면, the 시스템 **SHALL** 각 관심 종목에 대해 Phase A의 WebSocket을 구독하여 실시간 시세를 표시한다.
- **REQ-WL-008 (Event)**: **WHEN** 인증된 사용자가 추천 카드의 별표 아이콘을 토글하면, the 시스템 **SHALL** 해당 종목을 관심 목록에 추가 또는 제거하고 별표 상태를 즉시 갱신한다.
- **REQ-WL-009 (State)**: **WHILE** 사용자가 인증되지 않은 상태에서 추천 카드를 보는 경우, the 시스템 **SHALL** 별표 토글을 비활성화하거나 로그인 유도로 처리하고 관심 목록을 변경하지 않는다.

### 2.3 포트폴리오 AI 분석 (REQ-PAI) — Priority Medium

- **REQ-PAI-001 (Event)**: **WHEN** 인증된 사용자가 본인 포트폴리오에 대해 `POST /portfolios/{id}/ai-analysis`를 호출하면, the 시스템 **SHALL** 해당 포트폴리오의 보유 종목(섹터, 비중, 수익률)을 수집하여 Claude API(claude-haiku-4-5)에 분석을 요청한다.
- **REQ-PAI-002 (Ubiquitous)**: the 시스템 **SHALL** AI 분석 결과로 분산도 평가(diversification), 리스크 분석(risk), 개선 제안(suggestions)을 **한국어**로 반환한다.
- **REQ-PAI-003 (Ubiquitous)**: the 시스템 **SHALL** AI 분석 입력에 종목별 섹터·평가 비중·수익률과 전체 포트폴리오 요약을 포함하되, 사용자 식별 정보(이메일·이름 등)는 프롬프트에 포함하지 않는다.
- **REQ-PAI-004 (State)**: **WHILE** 사용자가 인증되지 않았거나 다른 사용자의 포트폴리오에 대해 분석을 요청하는 경우, the 시스템 **SHALL** 401 또는 403을 반환하고 분석을 수행하지 않는다.
- **REQ-PAI-005 (Unwanted)**: **IF** 포트폴리오에 보유 종목이 없으면, **THEN** the 시스템 **SHALL** Claude API를 호출하지 않고 "분석할 보유 종목이 없습니다" 취지의 응답을 반환한다.
- **REQ-PAI-006 (Unwanted)**: **IF** Claude API 호출이 실패하거나 타임아웃되면, **THEN** the 시스템 **SHALL** 5xx 대신 명확한 오류 메시지(분석 일시 불가)를 반환하고 실패를 로그하며, 포트폴리오 데이터는 변경하지 않는다.
- **REQ-PAI-007 (Ubiquitous)**: the 시스템 **SHALL** AI 분석 응답에 "본 분석은 투자 권유가 아닌 정보 제공 목적" 면책 문구를 포함한다.

### 2.4 프론트엔드 (REQ-FE)

- **REQ-FE-001 (Ubiquitous)**: the 시스템 **SHALL** `useLivePrice(krxCode)` 커스텀 훅을 제공하여 WebSocket 구독·해제와 최신 가격 상태를 관리한다.
- **REQ-FE-002 (Ubiquitous)**: the 시스템 **SHALL** 포트폴리오 보유 종목 행과 종목 상세 모달에 실시간 시세 배지(가격 + 등락률, 색상 구분)를 표시한다.
- **REQ-FE-003 (Ubiquitous)**: the 시스템 **SHALL** 관심 목록 페이지에서 관심 종목을 실시간 시세와 함께 목록으로 표시하고, 항목 삭제 기능을 제공한다.
- **REQ-FE-004 (Ubiquitous)**: the 시스템 **SHALL** 추천 카드에 별표 토글 아이콘을 추가하여 관심 목록 포함 여부를 시각적으로 표시한다.
- **REQ-FE-005 (Ubiquitous)**: the 시스템 **SHALL** 포트폴리오 페이지에 "AI 분석" 확장 섹션을 추가하여 분석 실행 버튼, 분산도·리스크·개선 제안 결과, 면책 문구를 표시한다.
- **REQ-FE-006 (Unwanted)**: **IF** WebSocket 연결이 끊기면, **THEN** the 시스템 **SHALL** 마지막 가격을 유지 표시하고 재연결을 시도하되, UI를 깨뜨리지 않는다.

### 2.5 비기능 요구사항 (REQ-NFR)

- **REQ-NFR-001 (Ubiquitous)**: the 시스템 **SHALL** 운영 환경에서 WebSocket을 보안 연결(WSS)로 처리한다.
- **REQ-NFR-002 (Ubiquitous)**: the 시스템 **SHALL** 다수 WebSocket 연결을 단일 비동기 이벤트 루프에서 비차단으로 처리하여 다른 API 응답을 블로킹하지 않는다.
- **REQ-NFR-003 (Ubiquitous)**: the 시스템 **SHALL** 실시간 시세 조회, 관심 목록 조작, AI 분석 요청 각 단계의 결과·실패를 구조화 로그로 남기되, 토큰·자격 증명 원문은 로그에 포함하지 않는다.
- **REQ-NFR-004 (Ubiquitous)**: the 시스템 **SHALL** Claude API 키 등 모든 시크릿을 환경 변수로 관리하고 버전 관리에 포함하지 않는다.
- **REQ-NFR-005 (Ubiquitous)**: the 시스템 **SHALL** Phase 4 기능 추가 시 SPEC-STOCK-001/002의 기존 API·테이블·동작을 변경 없이 유지한다(하위 호환).

---

## 3. Exclusions (What NOT to Build)

본 SPEC 범위에서 명시적으로 **제외**되는 항목:

- **자동 매매/주문 실행**: 증권사 API를 통한 실제 매수/매도 주문 기능은 **영구 제외**한다 (규제·책임 리스크).
- **실시간 틱 단위 스트리밍**: 거래소 직접 연동을 통한 틱(체결) 단위 스트리밍은 제외하며, FinanceDataReader 기반 약 10초 폴링 push로 한정한다.
- **해외 주식/암호화폐**: 한국 주식(KRX)과 국내 상장 ETF만 대상이며 해외 자산은 제외한다.
- **AI 분석 결과 영구 저장/이력 관리**: 본 SPEC의 AI 분석은 요청 시점 1회성 응답으로 한정하며, 분석 이력 테이블·시계열 추적은 제외한다.
- **관심 목록 가격 알림**: 관심 종목의 가격 도달 알림(텔레그램·푸시)은 별도 Phase로 연기한다.
- **이메일 알림·소셜 로그인(OAuth)**: 이전 SPEC과 동일하게 Phase 4 범위 밖이다.

---

## 4. 가정 및 제약 (Assumptions & Constraints)

ASSUMPTIONS I'M MAKING:
1. SPEC-STOCK-002의 JWT 인증(`users`, `get_current_user`)이 안정적으로 운영 중이며, Phase B/C가 이를 그대로 의존해도 된다고 가정한다.
2. FinanceDataReader가 약 10초 주기 폴링에 견딜 수 있는 빈도로 KRX 현재가를 제공하며, 장중 가격 갱신에 충분한 정확도라고 가정한다(장 마감 시간에는 종가가 유지됨).
3. SPEC-STOCK-001의 Claude API 연동 패턴(클라이언트·키 관리)을 AI 분석에 재사용할 수 있으며, `claude-haiku-4-5` 모델을 사용한다고 가정한다.
4. 포트폴리오 보유 종목의 섹터 정보는 기존 데이터(추천/언급 매핑 또는 종목 메타)로부터 획득 가능하다고 가정하며, 섹터 미상 종목은 "기타"로 처리한다.
5. MVP와 동일하게 단일 서버(또는 단일 컨테이너 세트) 운영을 가정하며, 대규모 동시 WebSocket 연결·수평 확장은 가정하지 않는다.

제약:
- 본 시스템은 **투자 정보 제공 도구**이며 투자 권유·자문이 아니다. 실시간 시세·관심 목록·AI 분석 화면 모두 면책 고지를 유지한다 (REQ-FE-005, REQ-PAI-007).
- 신규 테이블은 `watchlist_items` 1종(마이그레이션 0006)만 추가하며, 기존 테이블은 변경하지 않는다.
- 신규 기술 요소: FastAPI WebSocket(기존 FastAPI에 내장), 프론트엔드 네이티브 `WebSocket` API. 신규 외부 패키지 추가는 최소화한다.

---

## 5. 기술 접근 (Technical Approach)

### 5.1 데이터 모델 (신규 1종)

`watchlist_items` 테이블 (마이그레이션 0006):

| 컬럼 | 타입 | 제약 | 설명 |
|------|------|------|------|
| id | Integer | PK, autoincrement | 식별자 |
| user_id | Integer | FK(users.id, CASCADE), NOT NULL | 소유 사용자 |
| krx_code | String(10) | NOT NULL | KRX 종목코드 |
| added_at | TIMESTAMPTZ | server_default now() | 등록 시각 |

제약: `UNIQUE(user_id, krx_code)` — 동일 사용자의 중복 종목 방지 (REQ-WL-004).

기존 테이블(`users`, `portfolios`, `portfolio_holdings`, `recommendations`)은 **재사용만** 하며 스키마를 변경하지 않는다.

### 5.2 API 계약 (신규)

| 메서드 | 경로 | 인증 | 요청 | 응답 |
|--------|------|------|------|------|
| WS | `/ws/prices/{krx_code}` | 불필요(공개 시세) | — | `{krx_code, price, change_pct, timestamp}` 스트림 |
| GET | `/watchlist` | 필요 | — | `[{krx_code, added_at}]` |
| POST | `/watchlist` | 필요 | `{krx_code}` | 생성된 관심 항목 |
| DELETE | `/watchlist/{krx_code}` | 필요 | — | 204 / 상태 코드 |
| POST | `/portfolios/{id}/ai-analysis` | 필요 | — | `{diversification, risk, suggestions, disclaimer}` |

### 5.3 백엔드 구조 (신규 모듈)

- `realtime/price_feed.py`: 단일 종목 현재가 조회(FinanceDataReader) + 최신 가격 캐시(REQ-WS-007).
- `realtime/ws_router.py`: FastAPI WebSocket 엔드포인트, 연결당 10초 폴링 루프, 정리 처리(REQ-WS-001~006).
- `watchlist/models 참조`: `db/models.py`에 `WatchlistItem` 추가.
- `watchlist/service.py`, `watchlist/router.py`: 관심 목록 CRUD(REQ-WL-001~006).
- `portfolio/ai_analysis.py`: 포트폴리오 → Claude 프롬프트 구성 → 응답 파싱(REQ-PAI-001~007). 기존 `portfolio/router.py`에 엔드포인트 추가.

### 5.4 프론트엔드 구조 (신규/변경)

- `hooks/useLivePrice.ts`: WebSocket 구독 훅(REQ-FE-001, REQ-FE-006).
- `pages/Watchlist.tsx`: 관심 목록 페이지(REQ-FE-003) + 라우트 등록.
- `components/LivePriceBadge.tsx`: 실시간 시세 배지(REQ-FE-002).
- `components/WatchlistStar.tsx`: 추천 카드 별표 토글(REQ-FE-004) — 기존 추천 카드 컴포넌트에 삽입.
- `pages/Portfolio.tsx` 변경: "AI 분석" 확장 섹션 추가(REQ-FE-005).

### 5.5 의존성 (Dependencies)

- **Phase A (WebSocket)**: 독립적. FinanceDataReader 재사용. 먼저 구현.
- **Phase B (Watchlist)**: SPEC-STOCK-002의 JWT 인증에 의존(REQ-WL-005). 프론트 관심 목록 페이지는 Phase A의 WebSocket에 의존(REQ-WL-007).
- **Phase C (AI 분석)**: SPEC-STOCK-002의 포트폴리오 데이터(`portfolios`, `portfolio_holdings`)와 SPEC-STOCK-001의 Claude API 연동에 의존(REQ-PAI-001).

---

## 6. 수용 기준 요약 (Acceptance Summary)

### Phase A — WebSocket 실시간 시세
- 유효 종목 연결 시 즉시 1건 + 10초 주기 가격 push (REQ-WS-001/002/003).
- 잘못된 종목 코드는 오류 후 종료, 조회 실패 주기는 스킵 후 재시도, 연결 종료 시 자원 회수 (REQ-WS-004/005/006).

### Phase B — 종목 관심 목록
- 인증 사용자 CRUD 동작 및 (user_id, krx_code) 중복 방지 (REQ-WL-001~004).
- 미인증 401, 중복/미존재/타사용자 조작 거부 (REQ-WL-005/006).
- 관심 목록 페이지 실시간 시세 표시, 추천 카드 별표 토글 동작 (REQ-WL-007/008/009).

### Phase C — 포트폴리오 AI 분석
- 본인 포트폴리오 분석 시 한국어 분산·리스크·개선 제안 + 면책 반환 (REQ-PAI-001/002/007).
- 빈 포트폴리오는 Claude 미호출 안내, 인증·소유권 위반 거부, API 실패 시 명확한 오류 (REQ-PAI-004/005/006).

---

## 7. 우선순위 요약

| 우선순위 | 기능 | 근거 |
|---------|------|------|
| High | REQ-WS (WebSocket 실시간 시세) | 독립적, 관심 목록 페이지의 전제, 가장 먼저 구현 |
| Medium | REQ-WL (종목 관심 목록) | 인증·WebSocket에 의존 |
| Medium | REQ-PAI (포트폴리오 AI 분석) | 포트폴리오 데이터·Claude 연동에 의존 |
