# 한국 주식 & ETF 추천 시스템

자동으로 금융 뉴스를 수집하고, Claude AI로 감성 분석을 수행한 후, 실시간 시세 데이터와 결합하여 매일 한국 주식과 ETF 추천 리스트를 생성하는 지능형 투자 정보 플랫폼입니다.

## 핵심 기능

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

### 웹 대시보드
- **실시간 추천**: Top 10 주식 및 ETF 추천 리스트
- **상세 분석**: 종목별 추천 근거, 기여 뉴스, 점수 분해
- **섹터 트렌드**: Recharts 시계열 차트로 섹터별 뉴스 흐름 시각화
- **뉴스 피드**: 감성 배지가 포함된 최신 기사 피드
- **투명한 면책 고지**: 모든 화면에 투자 책임 면책 고지 표시

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
```

### 2. Docker Compose로 시작 (권장)

```bash
# 전체 시스템 시작 (PostgreSQL + Redis + 백엔드)
docker-compose up -d

# 데이터베이스 마이그레이션
docker-compose exec backend alembic upgrade head

# 로그 확인
docker-compose logs -f backend
```

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

### 추천 정보

| 메서드 | 경로 | 설명 | 응답 |
|--------|------|------|------|
| `GET` | `/recommendations` | Top 10 주식 추천 | `{ stocks: [ { krx_code, name, score, reason, ... } ], timestamp }` |
| `GET` | `/recommendations/{krx_code}` | 종목별 추천 근거 상세 | `{ krx_code, analysis, contributing_news, ... }` |

### 뉴스 및 트렌드

| 메서드 | 경로 | 설명 | 응답 |
|--------|------|------|------|
| `GET` | `/news?limit=N` | 분석 완료 뉴스 피드 | `{ news: [ { title, summary, sentiment, source, ... } ], total }` |
| `GET` | `/sectors/trends?days=N` | 섹터별 트렌드 시계열 | `{ trends: [ { sector, volume, sentiment, timestamp } ] }` |

### 헬스 체크

| 메서드 | 경로 | 설명 | 응답 |
|--------|------|------|------|
| `GET` | `/health` | 시스템 상태 확인 | `{ status, database, redis, last_update }` |

## 환경 변수

```bash
# 필수
ANTHROPIC_API_KEY="sk-..."              # Claude API 키

# 데이터베이스
DATABASE_URL="postgresql://user:password@localhost/ai_stock_picker"

# Redis (선택)
REDIS_URL="redis://localhost:6379/0"

# 로깅 (선택)
LOG_LEVEL="INFO"                         # DEBUG, INFO, WARNING, ERROR

# 스케줄러 (선택)
ENABLE_SCHEDULER="true"
SCHEDULER_DAILY_HOUR="6"                # 일일 배치 시간 (기본: 오전 6시)
SCHEDULER_INTRADAY_INTERVAL="30"        # 장중 갱신 간격 분 (기본: 30분)
```

## 프로젝트 구조

```
ai-stock-picker/
├── backend/
│   ├── src/stock_picker/
│   │   ├── api/                  # FastAPI 라우터
│   │   │   └── main.py           # 엔드포인트 정의
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
│   │   ├── db/                   # ORM 모델
│   │   │   ├── models.py         # 5개 테이블
│   │   │   └── session.py        # async 세션
│   │   ├── scheduler/            # 스케줄 설정
│   │   │   └── setup.py
│   │   └── main.py              # 앱 진입점
│   ├── tests/
│   │   ├── unit/                # 단위 테스트
│   │   └── integration/         # 통합 테스트
│   ├── pyproject.toml
│   └── alembic/                 # 마이그레이션
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── RecommendationList.tsx
│   │   │   ├── StockDetail.tsx
│   │   │   ├── SectorTrendChart.tsx
│   │   │   ├── EtfRecommendationList.tsx
│   │   │   ├── NewsFeed.tsx
│   │   │   ├── Disclaimer.tsx
│   │   │   └── DataPreparingState.tsx
│   │   ├── services/
│   │   │   └── api.ts           # API 클라이언트
│   │   ├── App.tsx
│   │   └── index.tsx
│   ├── package.json
│   └── tsconfig.json
├── docker-compose.yml
├── .env.example
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
| **테스트 커버리지** | >85% | 86.05% |
| **테스트 성공률** | 100% | 243/243 (100%) |
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

- **Phase 1 (현재)**: MVP - 일일 추천, 대시보드
- **Phase 2**: 푸시 알림, 사용자 계정, 즐겨찾기
- **Phase 3**: 백테스팅 엔진, 포트폴리오 시뮬레이터, 해외 자산 지원
