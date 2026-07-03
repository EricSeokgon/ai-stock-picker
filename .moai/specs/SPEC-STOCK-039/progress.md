# SPEC-STOCK-039 Progress

Status: COMPLETE
Version: v0.39.0
Completed: 2026-06-25

## Tasks

- [x] T-001: market_status.py — is_krx_open 순수 함수 (zoneinfo, @MX:ANCHOR)
- [x] T-002: schemas.py — MarketStatusResponse 스키마 추가
- [x] T-003: router.py — GET /portfolios/market-status 공개 엔드포인트
- [x] T-004: test_market_status_039.py 작성 (13개 테스트)
- [x] T-005: 모든 테스트 통과 (13/13)
- [x] T-006: 프론트엔드 폴링 훅 + 배지 컴포넌트 + Portfolio 페이지 통합
- [x] T-007: MX 태그 (@MX:ANCHOR × 1)
- [x] T-008: Sync (CHANGELOG, README, progress.md)

## Test Results

- 신규 테스트: 13/13 통과
- 전체 단위 테스트: 995 passed, 8 failed (pre-existing)
- scipy 미사용: 확인
- WebSocket 미사용: 확인
- 신규 DB 마이그레이션 없음: 확인
- 시장 상태 공개 접근: 확인

## Deliverables

### Backend Files
- `backend/src/stock_picker/portfolio/market_status.py` (신규)
- `backend/src/stock_picker/portfolio/schemas.py` (수정: MarketStatusResponse 추가)
- `backend/src/stock_picker/portfolio/router.py` (수정: GET /portfolios/market-status)
- `backend/tests/unit/test_market_status_039.py` (신규, 13개 테스트)

### Frontend Files
- `frontend/src/hooks/useMarketPolling.ts` (신규)
- `frontend/src/hooks/useMarketPolling.js` (신규)
- `frontend/src/components/MarketStatusBadge.tsx` (신규)
- `frontend/src/components/MarketStatusBadge.js` (신규)
- `frontend/src/api/portfolio.ts` (수정: apiGetMarketStatus)
- `frontend/src/api/portfolio.js` (수정: apiGetMarketStatus)
- `frontend/src/pages/Portfolio.tsx` (수정: 폴링 훅 + 배지 통합)
- `frontend/src/pages/Portfolio.js` (수정: 폴링 훅 + 배지 통합)

## Key Features

- **is_krx_open()**: zoneinfo 기반 KRX 장중 시간 판정 (평일 09:00~15:30 KST)
- **useMarketPolling()**: REST 폴링 훅 (기본 60초, in-flight 가드, cleanup)
- **MarketStatusBadge**: 장 중/마감 상태 + 마지막 갱신 시각 표시
- **GET /portfolios/market-status**: 공개 엔드포인트 (인증 불필요)
