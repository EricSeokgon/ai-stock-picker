---
name: project-frontend-stock-picker
description: ai-stock-picker 프론트엔드 구조 및 SPEC-STOCK-003 Phase D 구현 현황
metadata:
  type: project
---

## 스택

- React 18 + TypeScript + Vite + Recharts + React Router v6
- 테스트: Vitest + @testing-library/react
- 인증: AuthContext (src/auth/AuthContext.tsx), localStorage 토큰

## 파일 구조 주의사항

- .js/.tsx 중복 파일 존재 (src/api/auth.js + auth.ts 등) — .tsx/.ts 파일만 사용
- src/__tests__/ 에 테스트 파일 위치

## SPEC-STOCK-003 Phase D (TASK-011, TASK-012) 구현 완료 (2026-06-09)

### 신규 파일
- `src/hooks/useLivePrice.ts` — WebSocket 가격 스트림 훅, 5초 재연결
- `src/api/watchlist.ts` — 관심 목록 CRUD API 래퍼
- `src/components/LivePriceBadge.tsx` — 실시간 시세 배지 (양수=빨강, 음수=파랑)
- `src/components/WatchlistStar.tsx` — 관심 목록 별표 토글
- `src/pages/Watchlist.tsx` — 관심 목록 페이지

### 수정 파일
- `src/pages/Portfolio.tsx` — LivePriceBadge + AI 분석 섹션 추가
- `src/App.tsx` — /watchlist 라우트 + 네비게이션 링크 추가

### 테스트
- 65개 전체 통과
- 빌드 성공 (TypeScript 오류 없음)

## WebSocket 패턴

WebSocket URL: `ws://localhost:8000/ws/prices/{krxCode}`
- 재연결: onerror/onclose 시 5초 후 재시도
- unmount 시 `closedRef.current = true` 설정 후 ws.close() + clearTimeout

**Why:** reconnect 타이머 누수 방지를 위해 closedRef와 reconnectTimerRef 두 ref를 함께 사용
**How to apply:** WebSocket 훅 구현 시 동일 패턴 적용

## 한국 주식 색상 관례

- 상승: `#c62828` (빨간색)
- 하락: `#1565c0` (파란색)
- 보합: `#333` (검정)
