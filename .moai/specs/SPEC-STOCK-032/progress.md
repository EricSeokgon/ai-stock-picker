# SPEC-STOCK-032 Progress

## Status: COMPLETE

| Phase | Status | Date |
|-------|--------|------|
| Plan  | DONE   | 2026-06-23 |
| Run   | DONE   | 2026-06-23 |
| Sync  | DONE   | 2026-06-23 |

## Implementation Summary

- Tasks: T-001~T-007 완료
- Tests: 27/27 PASS (91% coverage)
- Commit: feature/SPEC-STOCK-032
- Files modified: 8

## Key Decisions

- orders 컬럼: JSONB 대신 Text (SQLite 테스트 호환)
- 예산 기본값: 미지정 시 포트폴리오 총 평가액(KRW)
- 목표 비중 출처: SPEC-028 optimize_portfolio 결과 재사용 (Claude 재호출 없음)
- 소유권 위반: 404 (코드베이스 관례)
- 수수료: 국내 0.015%, 해외 0.25% (market_type 기반 분기)
