# 한국 주식 & ETF 추천 시스템

자동으로 금융 뉴스를 수집하고, Claude AI로 감성 분석을 수행한 후, 실시간 시세 데이터와 결합하여 매일 한국 주식과 ETF 추천 리스트를 생성하는 지능형 투자 정보 플랫폼입니다.

## 핵심 기능

### Phase 21: 뉴스피드·AI 시장 템포 (v0.21.0)
- GET /news/market-sentiment — 24시간 시장 감성 집계 (강세/중립/약세 3단계)
- GET /news?krx_code= — 종목별 뉴스 필터 (기존 /news 확장, 기준일 기반)
- POST /news/fetch — 수동 뉴스 수집 트리거 (무인증)
- MarketSentimentWidget — 시장 감성 게이지 + 뉴스 리스트 + 즉시 갱신 (History.tsx 통합)
- Redis TTL 1800s 캐시 + graceful degradation
- 기존 articles 테이블·ClaudeAnalysisClient 재사용 (신규 마이그레이션 없음)

### Phase 20: 알림 시스템 (v0.20.0)
- POST/GET/PUT/DELETE /alerts 알림 CRUD — 목표가(target_price)·급등락(surge_drop)·배당일(ex_dividend) 알림 유형
- 알림 점검 서비스 — 목표가·급등락·배당일 조건 체크 + 멱등 알림 적재 (기존 notifications 테이블 재사용)
- APScheduler 10분 주기 check_alerts 스케줄러 + POST /alerts/check 수동 트리거
- 프론트엔드 /alerts 알림 설정 페이지 + NavBar 벨 아이콘 링크

### Phase 19: 배당 포트폴리오 분석 (v0.19.0)
- GET /portfolios/{id}/dividends API — 포트폴리오 배당 분석 엔드포인트
- 배당 서비스 — FinanceDataReader 베스트에포트 조회 + Redis TTL 86400s 캐시
- 배당 지표 — DPS, 배당수익률, 연간배당수입 추정, 12개월 배당 캘린더
- 배당 UI — 요약 카드 + 종목별 테이블 + 월별 지급 캘린더

### Phase 18: 종목 스크리너 (v0.18.0)
- PER, PBR, ROE, 시가총액, 배당수익률 기반 다중 조건 필터링
- 스크리너 프리셋 저장/불러오기 (최대 5개)
- 결과에서 원클릭 관심종목 추가

### 포트폴리오 성과 분석 (Phase 17 신규 — SPEC-STOCK-017)
- **수익률 기준 분류**: 고수익(≥+5%), 일반, 저수익(≤-5%)
- **섹터별 성과 집계**: 보유 종목 섹터 태그 기반 투자금 가중평균 수익률
- **recharts 도넛 차트**: 포트폴리오 고/일반/저수익 비율 시각화

### 실시간 주가 스트리밍 (Phase 16 신규 — SPEC-STOCK-016)
- **멀티플렉스 WebSocket** (`ws /ws/prices`): 단일 연결로 다수 종목 구독/해지
- **ConnectionManager**: 인메모리 구독 레지스트리, 심볼별 팬아웃
- **가격 브로드캐스트 루프**: 10초 주기 폴링, `REALTIME_PRICE_MOCK` 개발 모킹 지원
- **가격 알림 연동**: WatchlistAlert 임계 도달 → notifications 인박스 자동 생성
- **Watchlist 마이그레이션**: N개 WS 연결 → 단일 멀티플렉스 연결로 성능 개선
- **Dashboard 실시간 시세**: 추천 종목 실시간 가격 표시
- **기존 단일 종목 엔드포인트** (`/ws/prices/{krx_code}`) 무중단 유지
- **Graceful degradation**: WS 실패 시 마지막 알려진 값 유지
- **테스트**: 백엔드 34개 신규 (650 총 통과), 프론트엔드 179개 총 통과

### AI 투자 조언 고도화 (Phase 15 신규 — SPEC-STOCK-014)
- **포트폴리오 리밸런싱 제안**: 보유 주식·추천 비교 기반 AI 제안 (POST /advice/rebalance)
- **리스크 프로파일 분석**: 섹터 집중도 기반 리스크 점수 0~100 산출 (POST /advice/risk-profile)
- **맞춤형 시장 브리핑**: 1일 1회 캐시, Redis 키 `ai_advice:briefing:{user_id}:{date}` (GET /advice/market-briefing)
- **조언 이력 & 피드백**: AI 조언 영속 저장, helpful/not_helpful 품질 피드백 (GET /advice/history)
- **프론트엔드**: 포트폴리오 3탭 조언 패널 + /advice/history 이력 페이지
- **마이그레이션 0015**: `ai_advice` 테이블, UNIQUE(user_id, advice_type, ref_date) 멱등성 보장
- **면책 고지**: 모든 응답에 투자 면책 문구 포함, 자동 매매·실시간 데이터 스코프 외

### 알림·인박스 시스템 (Phase 14 신규 — SPEC-STOCK-013)
- **인앱 알림 인박스**: 가격 알림·추천 변경 이력을 앱 내부에 영속 저장, 미읽음/읽음 상태 관리
- **인박스 API**: `GET /notifications/inbox` 목록 조회, `PATCH` 읽음 처리, `GET /notifications/inbox/unread-count` 미읽음 배지
- **추천 변경 알림**: 관심 종목이 추천에 신규 진입(`rec_new`) / 이탈(`rec_dropped`) 시 자동 인박스 알림 생성
- **가격 알림 인박스 연동**: 기존 텔레그램/이메일 알림 발동 시 동시에 인박스 레코드 저장
- **NavBar 종 아이콘**: 미읽음 배지 표시 + 알림 인박스 페이지(`/notifications`), 비로그인 시 숨김
- **멱등 중복 방지**: `UNIQUE(user_id, type, krx_code, ref_date)` — 장중 30분 재실행에도 중복 알림 없음
- **마이그레이션 0014**: `notifications` 테이블 단일 추가, 인덱스 `(user_id, is_read, created_at DESC)` 최적화

### 섹터 분석 대시보드 (Phase 9 신규 — SPEC-STOCK-008)
- **섹터 집계 생산자**: 일별 AnalysisResult → sector_trends 자동 집계, trend_score = avg_sentiment×0.7 + log(volume+1)×0.3
- **섹터 순위 API**: `GET /sectors/ranking?sort=score|sentiment|volume` 실시간 섹터 랭킹
- **섹터 상세 API**: `GET /sectors/{sector}/detail` 트렌드 시계열 + 구성 종목 목록
- **섹터 분석 페이지**: React `/sectors` 라우트, 순위 표 + Recharts 트렌드 차트 + 상세 패널
- **파이프라인 통합**: 일일/장중 파이프라인에 섹터 집계 단계 삽입, 실패 무중단

### 종목 검색 · 상세 페이지 · 추천 품질 피드백 (Phase 8 신규 — SPEC-STOCK-007)
- **종목 검색 API**: `GET /stocks/search?q=` KRX 코드/이름 부분 일치, 추천 종목 우선 정렬, 최대 20개 반환
- **가격 시계열**: `GET /stocks/{krx_code}/prices?days=30` 30일 OHLCV 데이터, Redis TTL 3600s, graceful fallback
- **추천 피드백**: `POST/GET /recommendations/{krx_code}/feedback` up/down 투표, 집계, 선택적 JWT 인증
- **상세 페이지**: React `/stocks/:krxCode` 라우트, 종목명/차트/피드백 표시, 면책 고지 포함
- **가격 차트**: Recharts LineChart로 30일 시계열 OHLC 시각화, 피드백 버튼 통합

### 추천 근거 설명 & 히스토리 & 감성 라벨 (Phase 7 신규 — SPEC-STOCK-006)
- **Claude 자동 설명 생성**: 각 추천에 대해 Claude Haiku로 한국어 2~3문장 근거 자동 생성
- **추천 히스토리 조회**: `GET /recommendations/history?days=N` (기본 7일, 범위 1~90일)로 날짜별 추천 기록 조회
- **감성 5단계 라벨**: 뉴스 분석 결과에 매우긍정/긍정/중립/부정/매우부정 5단계 라벨 추가 (`sentiment_label`)
- **히스토리 페이지**: 7/14/30일 기간 선택, 날짜별 그룹화된 과거 추천 목록 표시
- **뉴스 감성 배지**: NewsFeed에 한국어 5단계 배지 표시, 기존 감성 배지 폴백 유지

### 성능 최적화 & UX 고도화 (Phase 6 — SPEC-STOCK-005)
- **Redis 파생 캐시**: 추천 결과 캐싱 (`recommendations:top:{limit}`, `recommendations:sector:{sector}`)
- **가격 Redis 캐시**: 실시간 시세 캐싱 (`price:{krx_code}`, TTL 60s)
- **필터링 & 정렬**: `GET /recommendations` with `limit`, `sector`, `sort`, `min_score` 파라미터
- **필터 UI**: 추천 화면에 필터바 추가 (섹터, 정렬, 최소 점수)
- **모바일 반응형**: 768px 이하 화면에서 햄버거 메뉴, 카드 레이아웃 최적화
- **포트폴리오 레이아웃**: 테이블 가로 스크롤 (모바일), 관심목록 컴팩트 카드

### 자동 뉴스 수집
- **일일 배치**: 매일 오전 6시 네이버 금융, 한국경제, 매일경제, 연합뉴스에서 신규 기사 수집
- **장중 갱신**: 09:00~15:30 30분 간격 증분 수집
- **멱등 처리**: URL 기준 중복 기사 자동 제거
- **부분 실패 격리**: 개별 소스 실패 시 다른 소스 계속 수집

### AI 감성 분석
- **Claude API 연동**: claude-sonnet-4-6 모델로 뉴스의 긍정/부정/중립 감성 분류
- **엔티티 추출**: 섹터 태그, 핵심 키워드, 1문장 요약 자동 생성
- **배치 처리**: 5개씩 묶음으로 처리하여 API 호출 최소화
- **강화된 스키마**: JSON 스키마 강제로 응답 일관성 보장
- **재시도 메커니즘**: 3회 지수 백오프로 안정성 극대화

### 지능형 추천 엔진
- **가중합산 점수**: 감성(40%) + 거래량(20%) + 모멘텀(25%) + 거래량 이상(15%)
- **시간 감쇠**: 최근 뉴스에 높은 가중치 부여(반감기 24시간)
- **ETF 추천**: 섹터 트렌드 기반 자동 ETF 매칭
- **근거 기반 설명**: 각 추천에 대한 상세 근거 제시

### 실시간 시세 스트리밍 (Phase 4 신규)
- **WebSocket 기반**: 웹소켓으로 종목별 실시간 시세 스트림 (10초 주기)
- **자동 재연결**: 네트워크 단절 시 자동 재연결 기능
- **자원 회수**: 구독 해지 시 즉시 리소스 정리

### 종목 관심 목록 (Phase 4 신규)
- **보관 기능**: 관심 있는 종목을 즐겨찾기로 저장
- **관리 기능**: 추가/삭제 기능 및 중복 방지
- **JWT 인증**: 사용자별 독립적인 관심 목록 관리

### 포트폴리오 AI 분석 (Phase 4 신규)
- **Claude AI 분석**: claude-haiku-4-5 모델로 포트폴리오 상세 분석
- **한국어 응답**: 투자 전략, 리스크 요인, 개선 제안 제시
- **면책 고지 포함**: 분석 결과와 함께 투자 책임 고지 제공
- **1회성 응답**: 분석 요청 시마다 최신 AI 분석 수행

### 관심 목록 가격 알림 (Phase 5 신규)
- **목표가 설정**: 이상(≥) / 이하(≤) 두 가지 방향 지원
- **자동 알림**: 목표가 도달 시 텔레그램으로 1회 통지
- **활성 알림 관리**: 알림별 상태 추적 및 삭제 기능
- **스케줄러**: 5분 주기 가격 모니터링

### 이메일 알림 (Phase 5 신규)
- **SMTP 기반**: 이메일 구독 관리 (추가/해지)
- **가격 도달 알림**: 목표가 달성 시 이메일 발송
- **주간 요약**: 매주 월요일 07:00 KST 추천 요약 발송
- **구독 상태**: 구독 활성화/해제 토글

### 웹 대시보드
- **실시간 추천**: Top 10 주식 및 ETF 추천 리스트
- **실시간 시세**: 관심 목록 및 포트폴리오 종목의 실시간 가격 표시 (색상 표기: 상승=빨강, 하락=파랑)
- **상세 분석**: 종목별 추천 근거, 기여 뉴스, 점수 분해
- **섹터 트렌드**: Recharts 시계열 차트로 섹터별 뉴스 흐름 시각화
- **뉴스 피드**: 감성 배지가 포함된 최신 기사 피드
- **포트폴리오 관리**: 실시간 종목 시세 포함 포트폴리오 성과 분석
- **AI 분석**: 포트폴리오의 AI 기반 상세 분석 결과 표시
- **투명한 면책 고지**: 모든 화면에 투자 책임 면책 고지 표시

## CI/CD 파이프라인 (Phase 12 신규 — SPEC-STOCK-011)

GitHub Actions를 통한 완전 자동화된 CI/CD 파이프라인:

### CI 워크플로 (`.github/workflows/ci.yml`)

**트리거**: `push` 및 `pull_request` (master 브랜치)

**병렬 잡**:

1. **백엔드 검사** (`backend-ci`)
   - ESLint 기반 Linting (ruff)
   - 컴파일 검증 (compileall)
   - 테스트 실행 (pytest, 85% 이상 커버리지 필수)
   - uv 패키지 캐싱

2. **프론트엔드 검사** (`frontend-ci`)
   - ESLint 9 flat config 검증
   - 테스트 실행 (vitest)
   - 운영 빌드 검증 (Vite build)
   - npm 캐싱

3. **Docker 빌드 검증** (`docker-build`)
   - 백엔드·프론트엔드 Dockerfile 빌드 (실제 푸시 없음)
   - GitHub Actions 캐시 활용

**배지**: [![CI](https://github.com/{owner}/ai-stock-picker/actions/workflows/ci.yml/badge.svg)](https://github.com/{owner}/ai-stock-picker/actions/workflows/ci.yml)

### CD 워크플로 (`.github/workflows/cd.yml`)

**트리거**: CI 워크플로 성공 후 master 브랜치에서만 실행

**자동 배포**:

- 백엔드 이미지: `ghcr.io/{owner}/ai-stock-picker-backend:latest` + `:{SHA}`
- 프론트엔드 이미지: `ghcr.io/{owner}/ai-stock-picker-frontend:latest` + `:{SHA}`
- GitHub Container Registry (ghcr.io)에 자동 푸시
- 인증: GitHub 기본 `GITHUB_TOKEN` 사용

**이미지 다운로드**:

```bash
# 최신 버전
docker pull ghcr.io/{owner}/ai-stock-picker-backend:latest
docker pull ghcr.io/{owner}/ai-stock-picker-frontend:latest

# 특정 버전
docker pull ghcr.io/{owner}/ai-stock-picker-backend:sha-abc123
```

## 아키텍처

```
┌─────────────────────────────────────────────────────┐
│                     웹 대시보드                      │
│            (React + TypeScript + Recharts)          │
└────────────────────────┬────────────────────────────┘
                         │
                    /recommendations
                    /news, /sectors/trends
                         │
┌────────────────────────▼────────────────────────────┐
│                   FastAPI 서비스층                  │
│              (RecommendationService)                │
└────────────────────────┬────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼──────┐ ┌──────▼────┐ ┌────────▼──┐
│  추천 레이어  │ │ 트렌드 계산 │ │ Redis    │
│ (Scoring     │ │ (Trending) │ │ (캐시)   │
│  Engine)     │ └─────────────┘ └──────────┘
└───────┬──────┘
        │
┌───────▼──────────────────────────────────┐
│   분석·매핑 레이어                       │
│ (ClaudeAnalysisClient, StockMapping,     │
│  FinanceDataReader, 섹터 트렌드)        │
└───────┬──────────────────────────────────┘
        │
┌───────▼──────────────────────────────────┐
│   수집 레이어                             │
│ (NewsCollector, SchedulerSetup)          │
│  RSS + 네이버 크롤링                     │
└───────┬──────────────────────────────────┘
        │
┌───────▼──────────────────────────────────┐
│   데이터 저장층                           │
│ (PostgreSQL + 5개 ORM 모델)             │
└──────────────────────────────────────────┘
```

## 기술 스택

| 계층 | 기술 |
|------|------|
| **언어** | Python 3.9+, TypeScript 5.x, JavaScript |
| **백엔드** | FastAPI 0.104+, SQLAlchemy 2.0+, APScheduler 3.10+ |
| **프론트엔드** | React 18.x, TypeScript, Axios, Recharts |
| **데이터베이스** | PostgreSQL 14+, Redis 7.x |
| **AI/ML** | Claude API (claude-sonnet-4-6) |
| **금융데이터** | FinanceDataReader, BeautifulSoup4, feedparser |
| **테스트** | pytest 7.x, Playwright, @testing-library/react |
| **배포** | Docker, docker-compose |

## 주요 업데이트 (최신: Phase 21 - 뉴스피드·AI 시장 템포)

**[0.21.0] - 2026-06-15** (SPEC-STOCK-021): 뉴스피드·AI 시장 템포 — 시장 감성 집계 + 종목별 뉴스 필터 + 무인증 수동 트리거

**[0.10.0] - 2026-06-10** (SPEC-STOCK-009): 추천 품질 개선 — 피드백 기반 가중치 + 스코어 투명성

### Phase 2: 사용자 기능 및 포트폴리오 (v0.2.0)

**[0.2.0] - 2026-06-09**에서는 다음 5가지 주요 기능이 추가되었습니다:

### Phase A — JWT 기반 사용자 인증
- 회원가입/로그인 엔드포인트 (bcrypt 암호 해싱, JWT 토큰)
- 접근 토큰(1시간) 및 갱신 토큰(7일) 발급
- 사용자 조회 및 토큰 갱신 API

### Phase B — 텔레그램 봇 알림
- 텔레그램 구독 모델 및 CRUD
- 봇 명령어: /start, /stop, /status, /recommend, /help
- 추천 변경 시 자동 알림 전송
- 백그라운드 데몬 스레드 기반 비동기 처리

### Phase C — 포트폴리오 시뮬레이터
- 포트폴리오 및 보유 종목 관리
- 실시간 종목별 성과 계산 (FinanceDataReader)
- 수익률, 손익금액, 가중평균 매입가 자동 계산
- 포트폴리오 성과 상세 분석 API

### Phase D — 백테스팅 엔진
- 과거 데이터 기반 전략 검증
- 모멘텀 및 거래량 전략 지원
- CAGR, 최대낙폭, 샤프지수 자동 계산
- 백테스트 결과 일별 추적

### Phase E — 프론트엔드 강화
- 인증 페이지 (로그인/회원가입)
- 포트폴리오 관리 페이지
- 백테스트 결과 시각화
- React Router 기반 라우팅

## 빠른 시작

### 1. 환경 준비

```bash
# 저장소 클론
git clone <repository-url>
cd ai-stock-picker

# 환경 변수 설정
cp .env.example .env

# .env 파일 편집 (필수)
# - ANTHROPIC_API_KEY: Claude API 키
# - DATABASE_URL: PostgreSQL 연결 문자열
# - REDIS_URL: Redis 연결 문자열 (선택, 기본값: redis://localhost:6379/0)
# - SECRET_KEY: JWT 토큰 서명용 비밀키 (권장)
# - TELEGRAM_BOT_TOKEN: 텔레그램 봇 토큰 (선택)
# - CORS_ORIGINS: 프론트엔드 오리진 (기본: http://localhost:3000)
# - SMTP_* (선택): 이메일 알림 설정
```

### 2. Docker Compose로 시작 (권장) — Phase 11 신규

```bash
# 전체 스택 시작: PostgreSQL + Redis + 백엔드 + 프론트엔드 (nginx)
docker-compose up -d

# 데이터베이스 마이그레이션 (자동으로 실행되지만, 필요 시 수동 실행)
docker-compose exec backend alembic upgrade head

# 시스템 상태 확인
curl http://localhost:8000/health

# 프론트엔드 접속
# http://localhost:3000 (브라우저)

# 로그 확인
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f db
```

**특징:**
- `docker compose up` **단일 명령**으로 전체 스택 기동
- 자동 헬스 체크로 서비스 준비 순서 보장
- DB/Redis 데이터는 named volume으로 영속화
- 프론트엔드는 nginx를 통해 SPA 라우팅 + `/api` 리버스 프록시 제공
- Redis 장애 시에도 백엔드는 graceful degradation 유지

### 3. 로컬 개발 환경 설정

**백엔드:**
```bash
cd backend

# Python 가상 환경 생성
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 의존성 설치
pip install -e ".[dev]"

# 데이터베이스 마이그레이션
alembic upgrade head

# 백엔드 실행 (http://localhost:8000)
uvicorn src.stock_picker.main:app --reload
```

**프론트엔드:**
```bash
cd frontend

# Node.js 의존성 설치
npm install

# 개발 서버 실행 (http://localhost:3000)
npm start
```

### 4. 초기 데이터 생성

```bash
# 백엔드 스케줄러 시작 (뉴스 수집 및 분석 자동 실행)
python -m src.stock_picker.scheduler

# 또는 수동 트리거
curl -X POST http://localhost:8000/health
```

## API 엔드포인트

### 인증 (Authentication)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/auth/register` | 회원가입 (username, password) |
| `POST` | `/auth/login` | 로그인 (username, password) → 액세스/갱신 토큰 |
| `POST` | `/auth/refresh` | 토큰 갱신 (refresh_token) → 새 액세스 토큰 |
| `GET` | `/auth/me` | 현재 사용자 정보 조회 (인증 필수) |

### 실시간 시세 (Real-time Price)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `WS` | `/ws/prices/{krx_code}` | 실시간 시세 스트림 (10초 주기) |

### 관심 목록 (Watchlist)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/watchlist` | 관심 목록 조회 (인증 필수) |
| `POST` | `/watchlist` | 종목 추가 (krx_code) (인증 필수) |
| `DELETE` | `/watchlist/{krx_code}` | 종목 삭제 (인증 필수) |

### 포트폴리오 관리 (Portfolio)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/portfolios` | 포트폴리오 목록 조회 (인증 필수) |
| `POST` | `/portfolios` | 포트폴리오 생성 (인증 필수) |
| `GET` | `/portfolios/{id}` | 포트폴리오 상세 조회 |
| `GET` | `/portfolios/{id}/holdings` | 보유 종목 목록 |
| `POST` | `/portfolios/{id}/holdings` | 종목 추가 |
| `DELETE` | `/portfolios/{id}/holdings/{holding_id}` | 종목 제거 |
| `GET` | `/portfolios/{id}/performance` | 포트폴리오 성과 분석 |
| `POST` | `/portfolios/{id}/ai-analysis` | 포트폴리오 AI 분석 (claude-haiku-4-5) (Phase 4 신규) |

### 백테스팅 (Backtesting) — Phase 13 완성 (SPEC-STOCK-012)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/backtest/run` | 백테스트 실행 (전략, 기간, universe_size, top_n) — HTTP 202 반환 |
| `GET` | `/backtest/runs` | 백테스트 이력 조회 |
| `GET` | `/backtest/runs/{id}` | 백테스트 결과 조회 (지표: cagr, max_drawdown, sharpe_ratio, total_return, win_rate) |
| `GET` | `/backtest/runs/{id}/results` | 일자 단위 가치 시계열 (date, portfolio_value, benchmark_value, daily_return) |

**주요 기능**:
- **전략 선택**: momentum (모멘텀) 또는 volume (거래량) 전략
- **종목 선택 파라미터**:
  - `universe_size`: 후보 종목 수 (기본값 정의)
  - `top_n`: 최종 포트폴리오에 포함할 상위 종목 수 (기본값 정의)
- **벤치마크 비교**: KOSPI(KS11) 및 KOSDAQ(KQ11) 지수 자동 수집
  - 동일 기준으로 정규화된 포트폴리오·벤치마크 가치 시계열
  - 벤치마크 데이터 미수집 시에도 백테스트 계속 진행 (benchmark_value=null)
- **성과 지표**: 
  - 누적 수익률(total_return): 최종 / 초기 가치 - 1
  - 승률(win_rate): 수익 양수 거래일 / 전체 거래일
  - CAGR, 최대 낙폭, 샤프 비율
  - 거래일 데이터 없을 시 안전한 기본값(0.0) 반환
- **상태 관리**: pending → running → done (또는 failed)

### 텔레그램 봇 (Telegram)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/telegram/subscribe` | 텔레그램 구독 (chat_id, user_id) |
| `POST` | `/telegram/unsubscribe` | 텔레그램 구독 취소 |
| `GET` | `/telegram/status/{chat_id}` | 구독 상태 확인 |

### 종목 검색 & 상세 정보 (SPEC-STOCK-007)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/stocks/search?q=` | 종목 검색 (KRX 코드/이름 부분 일치, 추천 우선) |
| `GET` | `/stocks/{krx_code}/prices?days=30` | 가격 시계열 (OHLCV, Redis 캐시) |
| `POST` | `/recommendations/{krx_code}/feedback` | 피드백 생성 (up/down 투표) |
| `GET` | `/recommendations/{krx_code}/feedback` | 피드백 조회 (집계 결과) |

### 추천 정보

| 메서드 | 경로 | 설명 | 응답 |
|--------|------|------|------|
| `GET` | `/recommendations` | Top 10 주식 추천 (필터 지원) | `{ stocks: [ { krx_code, name, score, reason, explanation, ... } ], timestamp }` |
| `GET` | `/recommendations/{krx_code}` | 종목별 추천 근거 상세 | `{ krx_code, analysis, contributing_news, explanation, ... }` |
| `GET` | `/recommendations/history?days=N` | 추천 히스토리 조회 (기본 7일) | `{ history: [ { trade_date, recommendations: [...] } ] }` |

**필터 파라미터** (SPEC-STOCK-005):
| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `limit` | int>0 | 반환할 추천 종목 수 (기본값: 10) |
| `sector` | str | 섹터 필터 (예: "전자", "금융", "화학") |
| `sort` | str | 정렬 순서: score \| sentiment \| volume (기본값: score) |
| `min_score` | float>=0 | 최소 종합 점수 (0~1) |

### 뉴스 및 시장 감성 (Phase 21 신규)

| 메서드 | 경로 | 설명 | 응답 |
|--------|------|------|------|
| `GET` | `/news/market-sentiment` | 시장 감성 집계 (24h) | `{ date, timestamp, sentiment, sentiment_level, total_articles, positive_count, neutral_count, negative_count, news: [...]  }` |
| `GET` | `/news?limit=N&krx_code=` | 뉴스 필터 (기존 + 종목 필터) | `{ news: [ { title, summary, sentiment, sentiment_label, source, krx_code, ... } ], total }` |
| `POST` | `/news/fetch` | 수동 뉴스 수집 트리거 (무인증) | `{ status: "started"\|"failed", message }` |
| `GET` | `/sectors/trends?days=N` | 섹터별 트렌드 시계열 | `{ trends: [ { sector, volume, sentiment, timestamp } ] }` |

### 헬스 체크

| 메서드 | 경로 | 설명 | 응답 |
|--------|------|------|------|
| `GET` | `/health` | 시스템 상태 확인 | `{ status, database, redis, last_update }` |

## 환경 변수

| 변수명 | 필수 | 기본값 | 설명 |
|--------|------|--------|------|
| `ANTHROPIC_API_KEY` | ✓ | - | Claude API 키 (sk-...) |
| `DATABASE_URL` | ✓ | - | PostgreSQL 연결 문자열 |
| `SECRET_KEY` | ✓ | - | JWT 토큰 서명용 비밀키 (임의의 문자열) |
| `REDIS_URL` | - | redis://localhost:6379/0 | Redis 연결 문자열 |
| `TELEGRAM_BOT_TOKEN` | - | - | 텔레그램 봇 토큰 |
| `LOG_LEVEL` | - | INFO | 로그 레벨 (DEBUG, INFO, WARNING, ERROR) |
| `ENABLE_SCHEDULER` | - | true | APScheduler 활성화 여부 (false, 0, no로 비활성화) |
| `REALTIME_PRICE_MOCK` | - | false | 실시간 가격 모킹 모드 (개발 환경용, true로 시뮬레이션 활성화) |
| `REALTIME_POLL_INTERVAL` | - | 10 | 실시간 가격 폴링 간격 (초) |
| `SCHEDULER_DAILY_HOUR` | - | 6 | 일일 배치 시간 (0~23) |
| `SCHEDULER_INTRADAY_INTERVAL` | - | 30 | 장중 갱신 간격 (분) |
| `SMTP_HOST` | - | - | SMTP 서버 호스트 (예: smtp.gmail.com) |
| `SMTP_PORT` | - | 587 | SMTP 포트 (보통 587 for TLS, 465 for SSL) |
| `SMTP_USER` | - | - | SMTP 사용자명 (이메일 주소) |
| `SMTP_PASSWORD` | - | - | SMTP 비밀번호 (앱 비밀번호 권장) |
| `SMTP_FROM` | - | - | 발신 이메일 주소 |
| `CORS_ORIGINS` | - | http://localhost:3000 | 프론트엔드 오리진 (Docker Compose 내부에서는 localhost, 운영 환경에서는 실제 도메인) |

**예제:**
```bash
ANTHROPIC_API_KEY="sk-proj-abc123..."
DATABASE_URL="postgresql://user:password@localhost/ai_stock_picker"
SECRET_KEY="your-secret-key-here-min-32-chars"
REDIS_URL="redis://localhost:6379/0"
TELEGRAM_BOT_TOKEN="123456789:ABCDefGHIjklmNOpqrsTUVwxyzABC123"
LOG_LEVEL="INFO"
ENABLE_SCHEDULER="true"
REALTIME_PRICE_MOCK="false"
REALTIME_POLL_INTERVAL="10"
SCHEDULER_DAILY_HOUR="6"
SCHEDULER_INTRADAY_INTERVAL="30"
CORS_ORIGINS="http://localhost:3000"
```

## 프로젝트 구조

```
ai-stock-picker/
├── backend/
│   ├── src/stock_picker/
│   │   ├── api/                  # FastAPI 라우터
│   │   │   └── main.py           # 전체 엔드포인트 정의
│   │   ├── auth/                 # JWT 인증 (Phase A)
│   │   │   ├── service.py        # 로그인, 회원가입, 토큰
│   │   │   ├── schemas.py        # Pydantic 모델
│   │   │   └── dependencies.py   # 인증 의존성
│   │   ├── collectors/           # 뉴스 수집
│   │   │   ├── rss_collector.py
│   │   │   ├── naver_collector.py
│   │   │   └── service.py
│   │   ├── analysis/             # Claude 감성 분석
│   │   │   ├── client.py
│   │   │   ├── worker.py
│   │   │   └── schema.py
│   │   ├── mapping/              # 종목 매핑
│   │   │   ├── krx_mapper.py
│   │   │   └── finance_reader.py
│   │   ├── scoring/              # 추천 점수 계산
│   │   │   ├── engine.py         # 가중합산
│   │   │   ├── normalize.py      # 정규화
│   │   │   └── reasoning.py      # 근거 생성
│   │   ├── recommendation/       # 추천 엔진
│   │   │   ├── service.py
│   │   │   ├── aggregator.py
│   │   │   ├── etf_recommender.py
│   │   │   ├── cache.py          # Redis 캐시
│   │   │   └── trending.py       # 섹터 트렌드
│   │   ├── realtime/             # 실시간 시세 스트리밍 (Phase 4 신규)
│   │   │   ├── price_feed.py     # FinanceDataReader 가격 조회
│   │   │   └── ws_router.py      # WebSocket 라우터
│   │   ├── watchlist/            # 관심 목록 (Phase 4 신규)
│   │   │   ├── models.py         # WatchlistItem ORM
│   │   │   ├── service.py        # CRUD 및 중복 방지
│   │   │   └── schemas.py        # API 스키마
│   │   ├── notifications/        # 알림 기능 (Phase 5 신규)
│   │   │   ├── alert_service.py  # WatchlistAlert CRUD
│   │   │   ├── alert_router.py   # /watchlist/alerts 라우터
│   │   │   ├── email_service.py  # SMTP 이메일 발송
│   │   │   ├── email_router.py   # /notifications/email 라우터
│   │   │   └── schemas.py        # 알림 Pydantic 모델
│   │   ├── portfolio/            # 포트폴리오 (Phase C)
│   │   │   ├── models.py         # Portfolio, PortfolioHolding
│   │   │   ├── service.py        # CRUD 및 성과 계산
│   │   │   ├── ai_analysis.py    # AI 분석 (Phase 4 신규)
│   │   │   └── schemas.py        # API 스키마
│   │   ├── backtest/             # 백테스팅 (Phase D)
│   │   │   ├── models.py         # BacktestRun, BacktestDailyResult
│   │   │   ├── engine.py         # 전략 실행
│   │   │   ├── strategies.py     # 모멘텀, 거래량 전략
│   │   │   └── service.py        # CRUD 및 분석
│   │   ├── telegram/             # 텔레그램 봇 (Phase B)
│   │   │   ├── bot.py            # 봇 핸들러
│   │   │   ├── models.py         # TelegramSubscription
│   │   │   ├── service.py        # 구독 관리
│   │   │   └── daemon.py         # 백그라운드 알림 스레드
│   │   ├── db/                   # ORM 모델
│   │   │   ├── models.py         # 모든 테이블 정의
│   │   │   └── session.py        # async 세션
│   │   ├── scheduler/            # 스케줄 설정
│   │   │   └── setup.py
│   │   └── main.py              # 앱 진입점
│   ├── tests/
│   │   ├── unit/                # 단위 테스트
│   │   │   ├── test_auth_service.py
│   │   │   ├── test_portfolio_service.py
│   │   │   ├── test_backtest_engine.py
│   │   │   └── ...
│   │   └── integration/         # 통합 테스트
│   │       └── test_auth_router.py
│   ├── pyproject.toml
│   └── alembic/                 # 마이그레이션
│       └── versions/
│           ├── 0002_users.py          # 사용자 테이블
│           ├── 0003_telegram_subs.py  # 텔레그램 구독
│           ├── 0004_portfolios.py     # 포트폴리오
│           ├── 0005_backtest.py       # 백테스팅
│           ├── 0006_watchlist.py      # 관심 목록 (Phase 4)
│           ├── 0007_watchlist_alerts.py     # 가격 알림 (Phase 5)
│           └── 0008_email_subscriptions.py  # 이메일 구독 (Phase 5)
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── RecommendationList.tsx
│   │   │   ├── StockDetail.tsx
│   │   │   ├── SectorTrendChart.tsx
│   │   │   ├── EtfRecommendationList.tsx
│   │   │   ├── NewsFeed.tsx
│   │   │   ├── Disclaimer.tsx
│   │   │   ├── DataPreparingState.tsx
│   │   │   ├── LivePriceBadge.tsx     # 실시간 시세 배지 (Phase 4 신규)
│   │   │   └── WatchlistStar.tsx      # 관심 목록 토글 (Phase 4 신규)
│   │   ├── hooks/
│   │   │   └── useLivePrice.ts       # WebSocket 시세 구독 훅 (Phase 4 신규)
│   │   ├── pages/
│   │   │   ├── Login.tsx         # 인증 페이지 (Phase E)
│   │   │   ├── Portfolio.tsx     # 포트폴리오 페이지 + 실시간 시세 + AI 분석 (Phase 4 강화)
│   │   │   ├── Watchlist.tsx     # 관심 목록 페이지 (Phase 4 신규)
│   │   │   ├── Backtest.tsx      # 백테스트 결과
│   │   │   └── Home.tsx          # 추천 대시보드
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx   # 인증 상태 관리
│   │   ├── services/
│   │   │   └── api.ts           # API 클라이언트
│   │   ├── App.tsx
│   │   └── index.tsx
│   ├── package.json
│   └── tsconfig.json
├── .moai/specs/SPEC-STOCK-002/spec.md  # Phase 2 요구사항
├── backend/docs/api.md           # API 상세 문서
├── docker-compose.yml
├── .env.example
├── CHANGELOG.md
└── README.md
```

## 개발 가이드

### 백엔드 테스트 실행

```bash
cd backend

# 전체 테스트
pytest

# 커버리지 리포트 생성
pytest --cov=src --cov-report=html

# 특정 테스트만 실행
pytest tests/unit/test_scoring.py -v
```

### 린트 및 포맷팅

```bash
cd backend

# 린트 검사 (ruff)
ruff check src tests

# 자동 포맷팅
black src tests

# 타입 검사
mypy src
```

### 프론트엔드 테스트

```bash
cd frontend

# 단위 테스트
npm test

# E2E 테스트
npm run test:e2e

# 빌드
npm run build
```

## 추천 점수 공식

### 주식 추천 점수

```
종합_점수 = 0.40 × 감성_점수
          + 0.20 × 거래량_점수
          + 0.25 × 모멘텀_점수
          + 0.15 × 거래량이상_점수
```

- **감성_점수**: 관련 뉴스의 평균 감성 (0~1)
- **거래량_점수**: 정규화된 뉴스 건수 (0~1)
- **모멘텀_점수**: 가격 상승률 기반 (0~1)
- **거래량이상_점수**: 전일 대비 거래량 이상 감지 (0~1)

### 섹터 트렌드 점수

```
섹터_트렌드 = (0.70 × 정규화_감성 + 0.30 × 정규화_거래량) × 시간_감쇠(반감기=24h)
```

### ETF 추천 점수

```
ETF_점수 = avg(관련_섹터의_트렌드_점수들)
```

## 성능 지표

| 지표 | 목표 | 현황 |
|------|------|------|
| **API 응답 시간** | <500ms (P95) | 실시간 측정 |
| **테스트 커버리지** | >85% | 91.5% |
| **테스트 성공률** | 100% | 394/394 (100%) |
| **일일 뉴스 수집** | 100~300건 | 동적 |
| **Claude API 처리** | 배치 단위 5개 | 최적화됨 |
| **캐시 히트율** | >70% | Redis 활성화 |

## 데이터 흐름

```
1. 뉴스 수집 (collectors/)
   RSS 피드 + 네이버 크롤링 → articles 테이블

2. 감성 분석 (analysis/)
   Claude API → analysis_results 테이블 (섹터, 감정, 키워드)

3. 종목 매핑 (mapping/)
   기사 텍스트 → KRX 코드 → stock_mentions 테이블
   FinanceDataReader → 시세 데이터

4. 트렌드 집계 (recommendation/trending.py)
   섹터별 감성 + 볼륨 → sector_trends 테이블

5. 추천 생성 (recommendation/)
   종목별 가중합산 → recommendations 테이블
   Redis 캐싱

6. 웹 서빙 (api/)
   GET /recommendations → 캐시된 Top 10
```

## 주의사항

### 투자 책임 면책 고지

본 시스템은 **투자 정보 제공 도구**이며 투자 권유, 자문, 또는 투자 판단을 위한 전문적 의견이 아닙니다. 

- 과거 뉴스 분석 결과가 미래 주가를 보장하지 않습니다
- 사용자는 독립적인 투자 판단 책임을 집니다
- 투자로 인한 손실에 대해 제공자는 책임을 지지 않습니다
- 실제 투자 전에 전문가 상담을 권장합니다

### 데이터 및 API 제한

- FinanceDataReader 시세: 약 15~20분 지연
- Claude API: 일일 호출 한도 내에서만 작동
- RSS 피드: 소스별로 업데이트 지연 가능
- 크롤링: robots.txt, 이용약관 준수 필수

### 운영 고려사항

- PostgreSQL 및 Redis 별도 운영 필요
- Claude API 키 보안 관리 필수
- 정기적인 데이터베이스 백업 권장
- 뉴스 수집 스케줄 안정성 모니터링

## 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능

## 지원

문제 발생 시:
1. `.moai/specs/SPEC-STOCK-001/spec.md` 요구사항 확인
2. 백엔드 로그 검토: `docker-compose logs backend`
3. 데이터베이스 연결 상태 확인: `GET /health`
4. 이슈 생성 시 에러 메시지, 재현 방법, 환경 정보 포함

## 로드맵

- **Phase 1** (완료): MVP - 일일 추천, 대시보드, 뉴스 분석
- **Phase 2** (완료, 2026-06-09):
  - Phase A: JWT 기반 사용자 인증 시스템
  - Phase B: 텔레그램 봇 알림 통합
  - Phase C: 포트폴리오 시뮬레이터
  - Phase D: 백테스팅 엔진 (전략 검증)
  - Phase E: 프론트엔드 강화 (인증, 라우팅)
- **Phase 3** (계획중): 
  - 포트폴리오 AI 최적화
  - 리스크 분석 및 상관관계 매트릭스
  - 해외 자산(미국주식, 암호화폐) 지원
- **Phase 4** (완료, 2026-06-09):
  - Phase A: WebSocket 기반 실시간 시세 스트리밍
  - Phase B: 종목 관심 목록 (관심 종목 저장 기능)
  - Phase C: 포트폴리오 AI 분석 (Claude haiku-4-5)
  - Phase D: 프론트엔드 강화 (실시간 시세 표시, 관심 목록 관리)
- **Phase 5** (완료, 2026-06-09):
  - Phase A: 관심 목록 가격 알림 (목표가 설정, 텔레그램 통지)
  - Phase B: 이메일 알림 (SMTP 기반, 주간 요약)
  - Phase C: 알림 관리 API (활성 알림 조회, 삭제)
  - Phase D: 스케줄러 강화 (5분 주기 가격 모니터링)
- **Phase 6** (완료, 2026-06-09 — SPEC-STOCK-005):
  - Phase A: Redis 파생 캐시 (추천, 섹터별)
  - Phase B: 가격 데이터 Redis 캐시 (60s TTL)
  - Phase C: 추천 필터링 & 정렬 API (limit, sector, sort, min_score)
  - Phase D: 프론트엔드 필터바 (섹터, 정렬, 최소 점수)
  - Phase E: 모바일 반응형 레이아웃 (햄버거 메뉴, 카드 레이아웃)
- **Phase 7** (완료, 2026-06-10 — SPEC-STOCK-006):
  - Phase A: Claude 추천 근거 설명 (한국어 2~3문장)
  - Phase B: 추천 히스토리 조회 API (`GET /recommendations/history?days=N`)
  - Phase C: 뉴스 감성 5단계 라벨 (매우긍정/긍정/중립/부정/매우부정)
  - Phase D: 히스토리 페이지 (7/14/30일 탭, 날짜별 그룹)
  - Phase E: 뉴스 피드 한국어 배지 (5단계, 폴백 유지)
- **Phase 8** (완료, 2026-06-10 — SPEC-STOCK-007):
  - Phase A: 종목 검색 API (GET /stocks/search)
  - Phase B: 가격 시계열 API + Redis 캐시
  - Phase C: 추천 피드백 API (up/down 투표)
  - Phase D: Alembic 0010 마이그레이션 (feedback 테이블)
  - Phase E: React 컴포넌트 4종 신규 (StockSearchBar, PriceChart, FeedbackButtons, StockDetailPage)
  - Phase F: 테스트 67건 추가 (backend 47 + frontend 20)
- **Phase 9** (완료, 2026-06-10 — SPEC-STOCK-008):
  - Phase A: 섹터 집계 생산자 (AnalysisResult → sector_trends)
  - Phase B: 섹터 API 확장 (GET /sectors/ranking, /sectors/{sector}/detail)
  - Phase C: 섹터 분석 페이지 React 신규
  - Phase D: SectorDetailPanel 컴포넌트 (트렌드 차트, 구성 종목)
  - Phase E: 파이프라인 통합 (일일/장중 갱신에 섹터 집계 삽입)
- **Phase 10** (완료, 2026-06-10 — SPEC-STOCK-009):
  - Phase A: Alembic 0012 마이그레이션 (base_score, feedback_score 컬럼)
  - Phase B: 피드백 계수 계산 (신뢰도 가중, MAX_ADJ=0.15)
  - Phase C: 피드백 일괄 집계 조회 (N+1 회피)
  - Phase D: 추천 파이프라인 피드백 조정 통합
  - Phase E: API 스키마 확장 (ScoreBreakdown, ScoreFactorContribution)
  - Phase F: ScoreBreakdown React 컴포넌트 신규
  - Phase G: 추천 목록 피드백 반영 배지 표시
  - Phase H: 백엔드 테스트 35건 + 프론트엔드 테스트 10건 추가
