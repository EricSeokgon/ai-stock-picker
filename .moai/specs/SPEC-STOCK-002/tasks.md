# Task Decomposition
SPEC: SPEC-STOCK-002

## 마일스톤

- **Phase A** (TASK-001~003): JWT 인증 인프라 — Priority High
- **Phase B** (TASK-004~006): 텔레그램 봇 — Priority High
- **Phase C** (TASK-007~009): 포트폴리오 시뮬레이터 — Priority Medium
- **Phase D** (TASK-010~012): 백테스팅 엔진 — Priority Low
- **Phase E** (TASK-013~015): 프론트엔드 — Priority Medium

## 설계 확정값
- JWT: `SECRET_KEY` 환경변수, `python-jose`, access 1h / refresh 7d
- Telegram: 폴링 방식, asyncio 루프 공유
- Portfolio: 조회 시점 실시간 시세 (FinanceDataReader)
- Backtest: `asyncio.create_task`, 상태는 `backtest_runs.status` 폴링

| ID | 설명 | Feature | 주요 파일 | 상태 |
|----|------|---------|----------|------|
| TASK-001 | users 테이블 + Alembic 마이그레이션 (0002) | JWT | db/models.py, 0002_users.py | done |
| TASK-002 | 비밀번호 해싱 + JWT 발급/검증 서비스 | JWT | auth/service.py, auth/schemas.py | done |
| TASK-003 | 인증 라우터 4종 + get_current_user 의존성 | JWT | auth/router.py, auth/dependencies.py | done |
| TASK-004 | telegram_subscriptions 테이블 + 마이그레이션 (0003) | Telegram | db/models.py, 0003_telegram_subs.py | done |
| TASK-005 | 봇 핸들러 5개 명령어 구현 | Telegram | telegram/handlers.py, telegram/bot.py | done |
| TASK-006 | 알림 전송기 + run_daily_pipeline 후크 연동 | Telegram | telegram/notifier.py, scheduler/jobs.py | done |
| TASK-007 | portfolios + portfolio_holdings 테이블 + 마이그레이션 (0004) | Portfolio | db/models.py, 0004_portfolios.py | done |
| TASK-008 | 포트폴리오 CRUD + 보유종목 서비스/라우터 | Portfolio | portfolio/service.py, portfolio/router.py | done |
| TASK-009 | 수익률 계산 (실시간 시세) | Portfolio | portfolio/service.py (performance) | done |
| TASK-010 | backtest_runs + backtest_daily_results 테이블 + 마이그레이션 (0005) | Backtest | db/models.py, 0005_backtest.py | done |
| TASK-011 | 모멘텀+거래량 백테스트 러너 + 지표 계산 | Backtest | backtest/runner.py, backtest/metrics.py | done |
| TASK-012 | 비동기 잡 실행 라우터 | Backtest | backtest/router.py | done |
| TASK-013 | 로그인/회원가입 페이지 + 인증 컨텍스트 | Frontend | pages/Login.tsx, auth/AuthContext.tsx | done |
| TASK-014 | 포트폴리오 관리 페이지 + 대시보드 위젯 | Frontend | pages/Portfolio.tsx, components/PortfolioSummary.tsx | done |
| TASK-015 | 백테스트 결과 페이지 (Recharts) | Frontend | pages/Backtest.tsx | done |
