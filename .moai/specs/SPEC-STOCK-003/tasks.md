# Task Decomposition
SPEC: SPEC-STOCK-003

## 마일스톤

- **Phase A** (TASK-001~003): WebSocket 실시간 시세 — Priority High
- **Phase B** (TASK-004~007): 종목 관심 목록(Watchlist) — Priority Medium
- **Phase C** (TASK-008~010): 포트폴리오 AI 분석 — Priority Medium
- **Phase D** (TASK-011~012): 프론트엔드 통합 — Priority Medium

## 설계 확정값
- 실시간 시세: FinanceDataReader 폴링, 연결당 약 10초 주기, 최신 가격 캐시 공유
- WebSocket 메시지: `{krx_code, price, change_pct, timestamp(ISO 8601)}` JSON
- Watchlist: 신규 테이블 `watchlist_items` (마이그레이션 0006), `UNIQUE(user_id, krx_code)`
- AI 분석: Claude `claude-haiku-4-5`, 1회성 응답(저장 없음), 한국어 출력, 면책 포함
- 인증: SPEC-STOCK-002의 `get_current_user` 의존성 재사용

## 의존성
- Phase A는 독립적이며 가장 먼저 구현 (Phase B 프론트가 이를 사용)
- Phase B는 JWT 인증(SPEC-STOCK-002)에 의존
- Phase C는 포트폴리오 데이터(SPEC-STOCK-002) + Claude 연동(SPEC-STOCK-001)에 의존

| ID | 설명 | Feature | 주요 파일 | 상태 |
|----|------|---------|----------|------|
| TASK-001 | 단일 종목 현재가 조회 + 최신 가격 캐시(전일 종가 대비 등락률 포함) | WebSocket | realtime/price_feed.py | pending |
| TASK-002 | FastAPI WebSocket 엔드포인트 `/ws/prices/{krx_code}` + 연결당 10초 폴링 루프 | WebSocket | realtime/ws_router.py, api/main.py | pending |
| TASK-003 | 연결 종료 자원 회수 + 잘못된 코드/조회 실패 처리 | WebSocket | realtime/ws_router.py | pending |
| TASK-004 | watchlist_items 테이블 + Alembic 마이그레이션 (0006) | Watchlist | db/models.py, 0006_watchlist.py | pending |
| TASK-005 | 관심 목록 서비스(추가/삭제/조회, 중복·소유권 검증) | Watchlist | watchlist/service.py, watchlist/schemas.py | pending |
| TASK-006 | 관심 목록 라우터 GET/POST/DELETE + 인증 의존성 | Watchlist | watchlist/router.py | pending |
| TASK-007 | 미인증 401 + 중복(409)/미존재(404)/타사용자(403) 거부 처리 | Watchlist | watchlist/router.py, watchlist/service.py | pending |
| TASK-008 | 포트폴리오 → AI 분석 입력 구성(섹터/비중/수익률, 사용자 식별정보 제외) | AI 분석 | portfolio/ai_analysis.py | pending |
| TASK-009 | Claude(claude-haiku-4-5) 호출 + 한국어 분산/리스크/제안 파싱 + 면책 | AI 분석 | portfolio/ai_analysis.py | pending |
| TASK-010 | POST /portfolios/{id}/ai-analysis 엔드포인트 + 빈 포트폴리오·실패·소유권 처리 | AI 분석 | portfolio/router.py | pending |
| TASK-011 | useLivePrice 훅 + LivePriceBadge + 포트폴리오/상세 모달 시세 배지 | Frontend | hooks/useLivePrice.ts, components/LivePriceBadge.tsx, pages/Portfolio.tsx | pending |
| TASK-012 | Watchlist 페이지 + 추천 카드 별표 토글 + 포트폴리오 AI 분석 섹션 | Frontend | pages/Watchlist.tsx, components/WatchlistStar.tsx, pages/Portfolio.tsx | pending |
