---
name: project-stock-frontend
description: ai-stock-picker 프론트엔드 구현 현황 - React 18, TypeScript, react-router-dom, Vitest 스택 (Phase E 완료)
metadata:
  type: project
---

프론트엔드 구현 완료 (TASK-013~015, Phase E).

**Why:** SPEC-STOCK-002 인증/포트폴리오/백테스트 기능 추가
**How to apply:** 추가 컴포넌트 작업 시 기존 인라인 CSS 패턴 + AuthContext useAuth() 훅 사용

## 핵심 패턴

- 인증: `useAuth()` 훅 → `src/auth/AuthContext.tsx` (localStorage 'stock_picker_token')
- 라우팅: react-router-dom v6, `MemoryRouter`로 감싸서 테스트
- 테스트: `vi.mock('../auth/AuthContext', ...)` + `vi.mock('../components/PortfolioSummary', ...)` 패턴 필수
- vitest include: `src/**/*.test.ts`, `src/**/*.test.tsx` 만 (`.js` 제외)
- tsconfig exclude: test 파일 + `src/test-setup.ts` 제외 (skipLibCheck: true)

## 주요 파일

### Phase A-D (기존)
- `src/api/client.ts` - 공개 API fetch 래퍼
- `src/App.tsx` - 라우팅 포함 메인 앱 (NavBar + Routes)
- `src/main.tsx` - BrowserRouter + AuthProvider 래핑
- `src/types.ts` - 도메인 타입

### Phase E (신규)
- `src/auth/AuthContext.tsx` - AuthProvider, useAuth 훅
- `src/api/auth.ts` - register/login/me API
- `src/api/portfolio.ts` - 포트폴리오 CRUD API
- `src/api/backtest.ts` - 백테스트 실행/조회 API
- `src/pages/Login.tsx` - 탭 전환 로그인/회원가입 폼
- `src/pages/Portfolio.tsx` - 포트폴리오 관리 + 보유종목 추가
- `src/pages/Backtest.tsx` - 백테스트 실행 + LineChart (recharts)
- `src/components/PortfolioSummary.tsx` - 대시보드 위젯

## 테스트 현황

- 총 48개 테스트 통과 (9개 파일)
- 빌드: TypeScript 에러 0개, `npm run build` 성공

## API 계약

- POST /auth/register, /auth/login → { access_token, token_type }
- GET /auth/me → UserInfo (Bearer 필요)
- GET/POST /portfolios → Portfolio[]
- POST /portfolios/{id}/holdings, GET /portfolios/{id}/performance
- POST /backtest/run, GET /backtest/runs, GET /backtest/runs/{id}/results
