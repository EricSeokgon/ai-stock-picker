---
id: SPEC-STOCK-001
version: 0.1.0
status: draft
created: 2026-06-01
updated: 2026-06-01
author: ircp
priority: high
---

# SPEC-STOCK-001: 구현 계획 (Implementation Plan)

## 1. 시스템 아키텍처

### 1.1 레이어 구성

```
┌──────────────────────────────────────────────────────────────────┐
│  프론트엔드 (React + Recharts)                                     │
│  - 추천 리스트 / 종목 상세 / 섹터 트렌드 차트 / 뉴스 피드          │
└───────────────────────────────┬──────────────────────────────────┘
                                 │ REST (JSON)
┌───────────────────────────────▼──────────────────────────────────┐
│  서비스 레이어 (FastAPI)                                          │
│  - /recommendations  /stocks/{code}  /sectors/trends  /news       │
│  - Redis 캐시 우선 조회, miss 시 PostgreSQL 조회                  │
└───────────────────────────────┬──────────────────────────────────┘
                                 │
       ┌─────────────────────────┼─────────────────────────┐
       ▼                         ▼                         ▼
┌──────────────┐        ┌──────────────────┐      ┌────────────────┐
│ 추천 레이어   │        │  분석 레이어      │      │ 수집 레이어     │
│ 스코어링      │◄───────│ Claude API 배치   │◄─────│ APScheduler    │
│ Redis 캐싱    │        │ 감성+섹터 태깅    │      │ RSS/크롤링      │
└──────┬───────┘        └────────┬─────────┘      └───────┬────────┘
       │                         │                        │
       └─────────────────────────┼────────────────────────┘
                                 ▼
                    ┌──────────────────────────┐
                    │  PostgreSQL (영속 저장)   │
                    │  articles / analysis /    │
                    │  stock_mentions /         │
                    │  recommendations /        │
                    │  sector_trends            │
                    └──────────────────────────┘
```

### 1.2 레이어별 책임

| 레이어 | 구성 요소 | 책임 | 대응 요구사항 |
|--------|-----------|------|--------------|
| 수집 | APScheduler, RSS 파서, 네이버 크롤러 | 오전 배치(06:00) + 장중 30분 증분 수집, 원문 저장 | REQ-NEWS-* |
| 분석 | Claude API 배치 워커 | 감성 분류, 섹터 태깅, 키워드/요약 추출, JSON 스키마 강제 | REQ-AI-* |
| 추천 | 트렌드 집계기, 스코어링 엔진, Redis 캐시 | 트렌드 스코어 산출, 종합 점수 계산, Top 10/ETF 추천 | REQ-TREND-*, REQ-MAP-*, REQ-REC-* |
| 서비스 | FastAPI REST API | 추천/트렌드/뉴스 조회 엔드포인트, 면책 고지 | REQ-WEB-*, REQ-NFR-001 |
| 프론트엔드 | React + Recharts | 대시보드 시각화 | REQ-WEB-* |

### 1.3 데이터 흐름 (일일 파이프라인)

1. **수집** (06:00): RSS/크롤링 → `articles` 저장 (URL 멱등)
2. **분석**: 미분석 기사 배치 → Claude API → `analysis_results` 저장
3. **매핑**: 종목명 → KRX 코드 → `stock_mentions`, FinanceDataReader 시세 조회
4. **트렌드 집계**: 섹터/테마별 볼륨·감성 → `sector_trends`
5. **추천**: 종합 점수 계산 → `recommendations` 저장 + Redis 캐시
6. **서비스**: 대시보드가 캐시/DB에서 조회하여 표시

---

## 2. 데이터 모델 (PostgreSQL)

### 2.1 articles (뉴스 기사)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | BIGSERIAL PK | 기사 ID |
| url | TEXT UNIQUE | 원문 URL (멱등 키) |
| source | VARCHAR(32) | naver / hankyung / mk / yonhap |
| title | TEXT | 제목 |
| content | TEXT | 본문 원문 |
| published_at | TIMESTAMPTZ | 발행 시각 |
| collected_at | TIMESTAMPTZ | 수집 시각 |
| status | VARCHAR(16) | collected / analyzed / analysis_failed |

인덱스: `url` (UNIQUE), `(status, published_at)`

### 2.2 analysis_results (Claude 분석 결과)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | BIGSERIAL PK | |
| article_id | BIGINT FK→articles | |
| sentiment | VARCHAR(8) | positive / negative / neutral |
| sentiment_score | NUMERIC(4,3) | -1.0 ~ +1.0 정규화 점수 |
| sector_tags | TEXT[] | 섹터 태그 배열 |
| keywords | TEXT[] | 핵심 키워드 배열 |
| summary | TEXT | 1문장 요약 |
| tokens_used | INT | 사용 토큰 수 (비용 추적) |
| analyzed_at | TIMESTAMPTZ | |

인덱스: `article_id`, GIN(`sector_tags`)

### 2.3 stock_mentions (종목 언급)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | BIGSERIAL PK | |
| article_id | BIGINT FK→articles | |
| stock_name | TEXT | 기사 내 종목명 |
| krx_code | VARCHAR(6) | KRX 종목 코드 (nullable=unmapped) |
| mention_status | VARCHAR(16) | mapped / unmapped |

인덱스: `(krx_code)`, `article_id`

### 2.4 sector_trends (섹터 트렌드)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | BIGSERIAL PK | |
| sector | VARCHAR(64) | 섹터/테마명 |
| trade_date | DATE | 집계 기준일 |
| news_volume | INT | 뉴스 건수 |
| avg_sentiment | NUMERIC(4,3) | 평균 감성 점수 |
| trend_score | NUMERIC(6,3) | 산출된 트렌드 스코어 |
| computed_at | TIMESTAMPTZ | |

인덱스: `(sector, trade_date)` UNIQUE

### 2.5 recommendations (추천 결과)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | BIGSERIAL PK | |
| trade_date | DATE | 추천 기준일 |
| asset_type | VARCHAR(8) | stock / etf |
| krx_code | VARCHAR(6) | 종목/ETF 코드 |
| rank | INT | 순위 (1~10) |
| total_score | NUMERIC(6,3) | 종합 추천 점수 |
| sentiment_score | NUMERIC(6,3) | 기여: 뉴스 감성 |
| volume_score | NUMERIC(6,3) | 기여: 뉴스 볼륨 |
| momentum_score | NUMERIC(6,3) | 기여: 가격 모멘텀 |
| anomaly_score | NUMERIC(6,3) | 기여: 거래량 이상 |
| reasoning | TEXT | 사람이 읽는 근거 설명 |
| computed_at | TIMESTAMPTZ | |

인덱스: `(trade_date, asset_type, rank)`

---

## 3. 추천 알고리즘 설계

### 3.1 종합 점수 공식 (주식)

```
total_score = 0.40 * sentiment_score   # 뉴스 감성 점수
            + 0.20 * volume_score      # 뉴스 볼륨 (언급 빈도)
            + 0.25 * momentum_score    # 가격 모멘텀
            + 0.15 * anomaly_score     # 거래량 이상
```

각 구성 점수는 0~1로 정규화 후 가중 합산한다.

| 구성 요소 | 정의 | 데이터 출처 |
|-----------|------|------------|
| sentiment_score | 해당 종목 언급 기사들의 평균 감성 점수(시간 감쇠 가중) | `analysis_results` |
| volume_score | 해당 종목 언급 건수의 min-max 정규화 | `stock_mentions` |
| momentum_score | 최근 N일 가격 변화율 정규화 | FinanceDataReader |
| anomaly_score | 당일 거래량 / 최근 평균 거래량 비율 정규화 | FinanceDataReader |

### 3.2 ETF 추천

ETF는 개별 종목 모멘텀 대신 **섹터 트렌드 스코어** 기반으로 추천한다.

```
etf_score = sector_trend_score(해당 ETF가 추종하는 섹터)
```

상위 트렌드 섹터를 추종하는 국내 상장 ETF를 매핑하여 추천 리스트를 구성한다.

### 3.3 근거 설명 생성

각 추천 항목의 `reasoning`은 기여도가 높은 구성 요소 + 대표 기사 요약을 조합하여 생성한다. 예: "반도체 섹터 긍정 뉴스 12건(평균 감성 +0.62)과 당일 거래량 평균 대비 1.8배 급증이 추천 근거입니다."

---

## 4. Claude API 활용 전략

### 4.1 프롬프트 설계

- **입력**: 기사 제목 + 본문(길이 제한 적용)
- **지시**: 감성 분류, 섹터 태깅, 키워드 추출, 1문장 요약을 **단일 호출**로 수행
- **출력 강제**: JSON 스키마 고정. 예시 스키마:

```json
{
  "sentiment": "positive | negative | neutral",
  "sentiment_score": -1.0,
  "sector_tags": ["반도체", "AI"],
  "keywords": ["HBM", "수출 증가"],
  "summary": "한 문장 요약"
}
```

### 4.2 비용 최적화

- **배치 처리** (REQ-AI-004): 여러 기사를 한 호출에 묶거나 워커 풀로 병렬 처리하여 호출 오버헤드 감소
- **본문 길이 제한**: 긴 기사는 앞부분 위주로 잘라 토큰 절감, 짧은 기사 우선 처리
- **캐싱**: 동일/유사 기사(URL 멱등)는 재분석하지 않음
- **토큰 추적** (REQ-NFR-003): `tokens_used` 기록으로 일일 비용 모니터링

### 4.3 견고성

- JSON 스키마 검증 실패 시 재시도, 최종 실패는 `analysis_failed` 처리 (REQ-AI-005)
- 지수 백오프 재시도 최대 3회

---

## 5. 구현 단계 (Phase별)

> 시간 추정 대신 우선순위와 단계 순서로 표기.

### Phase 1 — MVP (Priority: High)

목표: 수집 → 분석 → 기본 추천 → 단순 대시보드의 end-to-end 동작.

- 데이터 모델 5개 테이블 마이그레이션
- RSS/네이버 수집기 + APScheduler 오전 배치 (REQ-NEWS-001,003~006)
- Claude API 단일 기사 분석 + JSON 스키마 강제 (REQ-AI-001~003,005,006)
- 종목 매핑 + FinanceDataReader 시세 (REQ-MAP-*)
- 종합 스코어링 + Top 10 주식 추천 (REQ-REC-001,002,004,005)
- FastAPI `/recommendations`, `/news` + 단순 React 리스트 화면 + 면책 고지 (REQ-WEB-001,004,005)

### Phase 2 — 실시간성 & 시각화 (Priority: Medium)

- 장중 30분 증분 수집 + 추천 재계산 (REQ-NEWS-002, REQ-REC-006)
- 배치 분석 최적화 (REQ-AI-004)
- 섹터 트렌드 집계 + Recharts 차트 (REQ-TREND-*, REQ-WEB-003)
- 추천 근거 상세 화면 (REQ-WEB-002)
- ETF 추천 (REQ-REC-003)
- Redis 캐싱 강화 + P95 응답 목표 (REQ-NFR-001)

### Phase 3 — 확장 기능 (Priority: Low, 본 SPEC Exclusions)

- 백테스팅, 알림, 포트폴리오 시뮬레이터 (별도 SPEC으로 분리 예정)

---

## 6. 기술적 고려사항 및 리스크

| 리스크 | 영향 | 완화 전략 |
|--------|------|----------|
| 크롤링 차단 (403/429) | 수집 중단 | User-Agent 설정, 요청 throttle, 소스별 격리 실패 처리(REQ-NEWS-005,006), RSS 우선 활용 |
| 사이트 구조 변경 | 파서 깨짐 | 파서를 소스별 모듈화, 수집 실패 알림 로그 |
| Claude API 비용 폭증 | 운영비 부담 | 배치/길이 제한/캐싱, 일일 토큰 한도 모니터링(REQ-NFR-003) |
| 종목명→코드 매핑 실패 | 추천 누락 | KRX 종목 마스터 테이블 유지, unmapped 격리(REQ-MAP-003) |
| 시세 데이터 지연 | 모멘텀 정확도 저하 | 데이터 freshness 표기, 갱신 시각 노출(REQ-WEB-006) |
| 투자 책임 분쟁 | 법적 리스크 | 전 화면 면책 고지(REQ-WEB-005), "정보 제공 도구" 명시 |
| 데이터 freshness vs 정확도 | 추천 신뢰도 | 30분 갱신 주기 채택, 캐시 TTL과 재계산 정책 명확화 |

---

## 7. 외부 의존성

| 의존성 | 용도 | 비고 |
|--------|------|------|
| Claude API (claude-sonnet-4-6) | 감성/섹터/키워드 분석 | 키는 환경 변수 (REQ-NFR-002) |
| FinanceDataReader | KRX 시세/거래량 | 일/장중 데이터 |
| 네이버 금융 / RSS (한경·매경·연합) | 뉴스 원문 | robots.txt·약관 준수 |
| PostgreSQL | 영속 저장 | |
| Redis | 추천 캐시 | |
| APScheduler | 스케줄링 | |
