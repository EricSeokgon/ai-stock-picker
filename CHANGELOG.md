# Changelog

모든 주목할만한 변경 사항이 이 파일에 기록됩니다.

형식은 [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)를 따르며,
버전 관리는 [Semantic Versioning](https://semver.org/lang/ko/)을 따릅니다.

---

## [0.2.0] - 2026-06-09

### Added (Phase 2: 사용자 기능 및 포트폴리오 관리)

#### Phase A: JWT 기반 사용자 인증
- **사용자 모델 및 인증**
  - User 모델 (Integer PK, bcrypt 암호 해싱)
  - JWT 토큰 서명 (python-jose)
  - 액세스 토큰 (1시간), 갱신 토큰 (7일)
  - 토큰 갱신 메커니즘 (rotate-on-refresh)

- **인증 엔드포인트**
  - `POST /auth/register`: 회원가입 (username 중복 검사)
  - `POST /auth/login`: 로그인 (암호 검증 후 토큰 발급)
  - `POST /auth/refresh`: 토큰 갱신
  - `GET /auth/me`: 현재 사용자 정보 조회

- **데이터베이스**
  - `users` 테이블 (id, username, hashed_password, created_at)
  - Alembic 마이그레이션 (0002_users.py)

#### Phase B: 텔레그램 봇 알림
- **텔레그램 구독 관리**
  - TelegramSubscription 모델 (chat_id, user_id, created_at)
  - 구독/구독취소 CRUD 엔드포인트

- **봇 명령어 핸들러**
  - `/start`: 봇 시작 (chat_id 등록)
  - `/stop`: 구독 취소
  - `/status`: 현재 구독 상태 확인
  - `/recommend`: 최신 추천 5개 조회
  - `/help`: 사용 가능한 명령어 안내

- **자동 알림 시스템**
  - 백그라운드 데몬 스레드 (notify_subscribers_sync)
  - 추천 순위 변동 시 자동 푸시 (Telegram API)
  - 비동기 non-blocking 처리

- **데이터베이스**
  - `telegram_subscriptions` 테이블
  - Alembic 마이그레이션 (0003_telegram_subs.py)

#### Phase C: 포트폴리오 시뮬레이터
- **포트폴리오 관리**
  - Portfolio 모델 (user_id, name, description, created_at)
  - PortfolioHolding 모델 (krx_code, quantity, purchase_price, purchase_date)

- **포트폴리오 CRUD**
  - `GET /portfolios`: 사용자 포트폴리오 목록
  - `POST /portfolios`: 새 포트폴리오 생성
  - `GET/DELETE /portfolios/{id}`: 포트폴리오 상세 조회/삭제

- **보유 종목 관리**
  - `GET /portfolios/{id}/holdings`: 보유 종목 목록
  - `POST /portfolios/{id}/holdings`: 종목 추가
  - `DELETE /portfolios/{id}/holdings/{holding_id}`: 종목 제거

- **성과 계산**
  - 실시간 시가 조회 (FinanceDataReader)
  - 수익률 (%)  및 손익금액 자동 계산
  - 가중평균 매입가, 현재 총 평가액, 총 매입금액 계산
  - `GET /portfolios/{id}/performance`: 성과 분석 API

- **데이터베이스**
  - `portfolios`, `portfolio_holdings` 테이블
  - Alembic 마이그레이션 (0004_portfolios.py)

#### Phase D: 백테스팅 엔진
- **전략 실행 엔진**
  - BacktestRun 모델 (user_id, strategy, start_date, end_date, status)
  - BacktestDailyResult 모델 (시간별 포트폴리오 가치)

- **포함된 전략**
  - 모멘텀 전략: 가격 상승률 기반 매수/매도 신호
  - 거래량 전략: 거래량 이상 기반 매수 신호

- **성과 메트릭**
  - CAGR (연복합 성장률)
  - 최대 낙폭 (Maximum Drawdown)
  - 샤프 지수 (Sharpe Ratio)
  - 연간 수익률 및 변동성

- **백테스트 API**
  - `POST /backtest/run`: 백테스트 실행 (전략, 기간, 종목 선택)
  - `GET /backtest/runs`: 백테스트 이력 조회
  - `GET /backtest/runs/{id}`: 개별 백테스트 결과
  - `GET /backtest/runs/{id}/results`: 일별 상세 결과

- **비동기 처리**
  - asyncio.create_task로 백그라운드 실행
  - 실시간 진행률 조회 가능

- **데이터베이스**
  - `backtest_runs`, `backtest_daily_results` 테이블
  - Alembic 마이그레이션 (0005_backtest.py)

#### Phase E: 프론트엔드 강화
- **인증 페이지**
  - 로그인 페이지 (pages/Login.tsx)
  - 회원가입 페이지 (탭 형식으로 통합)
  - 토큰 localStorage 저장

- **상태 관리**
  - AuthContext: 전역 인증 상태 (login, register, logout)
  - 보호된 라우트 (ProtectedRoute)

- **포트폴리오 관리 페이지**
  - pages/Portfolio.tsx
  - PortfolioSummary 위젯 (총 평가액, 손익금액, 수익률)
  - 보유 종목 목록 (추가, 삭제)

- **백테스트 결과 페이지**
  - pages/Backtest.tsx
  - 백테스트 실행 폼 (전략, 기간 선택)
  - Recharts LineChart로 포트폴리오 가치 변화 시각화

- **라우팅**
  - react-router-dom v6
  - NavBar에서 페이지 전환
  - 인증 필수 페이지 보호

#### 기존 기능 강화
- **뉴스 수집 개선**
  - 4개 RSS 소스 (네이버 금융, 한국경제, 매일경제, 연합뉴스) 병렬 수집
  - URL 기준 멱등 처리로 중복 기사 100% 제거
  - 개별 소스 실패 격리

- **Claude 감성 분석**
  - claude-sonnet-4-6 모델
  - JSON 스키마 강제, 배치 처리, 지수 백오프 재시도

- **추천 엔진**
  - 가중합산 점수 (감성 40% + 거래량 20% + 모멘텀 25% + 이상거래량 15%)
  - 시간 감쇠 적용 (반감기 24시간)
  - 섹터 트렌드 집계, ETF 추천 자동화

#### 테스트 및 품질 보증
- **총 243개 테스트** (백엔드)
  - Auth 서비스: 회원가입, 로그인, 토큰 갱신 테스트
  - Portfolio 서비스: 포트폴리오/보유종목 CRUD, 성과 계산
  - Backtest 엔진: 전략 실행, 메트릭 계산
  - 기존 기능: 수집, 분석, 추천 (195개)

- **테스트 커버리지: 86.05%+**
  - 모든 새로운 기능 100% 커버리지

#### 데이터베이스 확장
- **새로운 테이블**
  - `users`: 사용자 계정
  - `telegram_subscriptions`: 텔레그램 구독
  - `portfolios`: 포트폴리오
  - `portfolio_holdings`: 보유 종목
  - `backtest_runs`: 백테스트 실행 기록
  - `backtest_daily_results`: 일별 백테스트 결과

- **마이그레이션**
  - 0002_users.py, 0003_telegram_subs.py, 0004_portfolios.py, 0005_backtest.py

#### 문서화 및 API
- **API 문서**: `/auth`, `/portfolio`, `/backtest`, `/telegram` 전체 정의
- **환경 변수**: SECRET_KEY, TELEGRAM_BOT_TOKEN 추가
- **아키텍처 다이어그램**: 6개 계층 (인증, 포트폴리오, 백테스팅 추가)

### Changed

- 뉴스 수집: BeautifulSoup4 및 feedparser 업그레이드
- 감성 분석: claude-sonnet-4-6으로 모델 업그레이드 (비용 효율, 품질 개선)
- 캐싱: Redis 연결 풀 최적화 (동시성 향상)
- API 응답: 전체 응답 구조 표준화

### Fixed

- 중복 기사 저장 버그: URL 유니크 제약 추가
- 종목 매핑 실패: 부분 매칭 로직 개선
- 시간대 처리: UTC/KST 타임존 명확화
- 비정상 거래량 감지: 임계값 미세 조정

### Deprecated

- REST API v1 (v2로 통합)

---

## [0.1.0] - 2026-06-01

### Added (Phase 1: MVP)

#### 핵심 기능
- **뉴스 수집 엔진**
  - 네이버 금융, 한국경제, 매일경제, 연합뉴스 RSS 피드 파싱
  - 매일 오전 6시 전체 수집, 09:00~15:30 30분 간격 증분 수집

- **AI 감성 분석**
  - Claude API (claude-sonnet-4-6) 연동
  - 뉴스 감성 분류 (긍정/부정/중립)
  - 섹터 태그 추출, 핵심 키워드 추출, 1문장 요약

- **주식/ETF 추천 엔진**
  - KRX 종목 코드 매핑
  - FinanceDataReader 시세 조회
  - 가중합산 점수 계산 (감성 40% + 거래량 20% + 모멘텀 25% + 이상거래량 15%)
  - Top 10 주식 추천 생성
  - 섹터 트렌드 기반 ETF 추천

- **웹 대시보드**
  - React + TypeScript 프론트엔드
  - Top 10 주식 추천 리스트
  - 종목별 상세 분석 모달
  - 섹터 트렌드 시계열 차트 (Recharts)
  - 최신 뉴스 피드 (감성 배지)
  - ETF 추천 섹션
  - 투자 책임 면책 고지

- **REST API**
  - `/recommendations`: 추천 리스트
  - `/recommendations/{krx_code}`: 종목별 상세 정보
  - `/news`: 뉴스 피드
  - `/sectors/trends`: 섹터 트렌드
  - `/health`: 헬스 체크

#### 인프라 및 배포
- **FastAPI 백엔드**
  - 비동기 요청 처리
  - 구조화 로깅

- **PostgreSQL 데이터베이스**
  - 5개 ORM 모델 (articles, analysis_results, stock_mentions, sector_trends, recommendations)
  - Alembic 마이그레이션

- **Redis 캐싱**
  - 추천 결과 캐싱 (TTL 1시간)

- **Docker & Docker Compose**
  - PostgreSQL, Redis, 백엔드 컨테이너 통합
  - 원클릭 시작: `docker-compose up`

- **APScheduler**
  - 일일 배치 (오전 6시)
  - 장중 갱신 (30분 간격)

#### 테스트 및 품질
- **195개 유닛 테스트** (백엔드)
  - 수집, 분석, 매핑, 스코어링, 추천 로직
  - Mock 객체 활용

- **48개 컴포넌트 테스트** (프론트엔드)
  - React 컴포넌트 렌더링, 상태 관리
  - 사용자 상호작용

- **통합 테스트**
  - API 엔드포인트 검증
  - 데이터베이스 쿼리 검증

- **코드 커버리지: 86.05%**

#### 문서화
- **README**: 프로젝트 개요, 빠른 시작, 아키텍처
- **API 문서**: 모든 엔드포인트 정의
- **개발 가이드**: 로컬 환경 설정, 테스트 실행

### Security

- Claude API 키 환경 변수로 관리
- 데이터베이스 연결 문자열 환경 변수로 관리
- SQL Injection 방지 (SQLAlchemy ORM)

### Known Limitations

- 사용자 인증/계정 시스템 없음 (공개 대시보드)
- 자동 매매 기능 미지원
- 백테스팅 엔진 미지원
- 해외 주식/암호화폐 미지원
- 실시간 틱 데이터 스트리밍 미지원 (30분 갱신)

---

## Unreleased

### Planned (Phase 2 향후 계획)

- 사용자 계정 및 개인화 (로그인, 즐겨찾기)
- 푸시/이메일 알림
- 백테스팅 엔진 (과거 데이터 검증)
- 포트폴리오 시뮬레이터
- 해외 주식 지원
- 실시간 시세 WebSocket 스트리밍
