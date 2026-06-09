# API 레퍼런스

한국 주식 & ETF 추천 시스템의 REST API 상세 문서입니다. (v0.2.0+)

## 기본 정보

- **기본 URL**: `http://localhost:8000` (로컬) / `https://api.example.com` (프로덕션)
- **응답 형식**: JSON
- **인증**: JWT Bearer Token (인증 필요 엔드포인트 참조)
- **캐싱**: 모든 응답에 적절한 Cache-Control 헤더 포함
- **버전**: API v1 (기본)

---

## API 엔드포인트

### 0. 인증 (Authentication)

#### 0.1 회원가입

```http
POST /auth/register
```

**설명**: 새로운 사용자 계정을 생성합니다.

**요청 본문**:
```json
{
  "username": "myuser",
  "password": "securepassword123"
}
```

**응답 스키마**:
```json
{
  "id": 1,
  "username": "myuser",
  "created_at": "2026-06-09T10:30:00Z",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**상태 코드**:
- `201 Created`: 회원가입 성공
- `400 Bad Request`: 이미 존재하는 username 또는 유효하지 않은 입력
- `500 Internal Server Error`: 서버 오류

**예제**:
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "myuser", "password": "securepassword123"}'
```

---

#### 0.2 로그인

```http
POST /auth/login
```

**설명**: 기존 사용자가 로그인하여 토큰을 획득합니다.

**요청 본문**:
```json
{
  "username": "myuser",
  "password": "securepassword123"
}
```

**응답 스키마**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**상태 코드**:
- `200 OK`: 로그인 성공
- `401 Unauthorized`: 잘못된 username 또는 password
- `400 Bad Request`: 형식 오류

**예제**:
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "myuser", "password": "securepassword123"}'
```

---

#### 0.3 토큰 갱신

```http
POST /auth/refresh
```

**설명**: 만료된 액세스 토큰을 갱신합니다. 갱신 토큰을 사용합니다.

**요청 본문**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**응답 스키마**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**상태 코드**:
- `200 OK`: 토큰 갱신 성공
- `401 Unauthorized`: 유효하지 않은 또는 만료된 갱신 토큰
- `400 Bad Request`: 형식 오류

**예제**:
```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "eyJ..."}'
```

---

#### 0.4 현재 사용자 정보

```http
GET /auth/me
```

**설명**: 현재 로그인한 사용자의 정보를 조회합니다. (인증 필수)

**요청 헤더**:
```
Authorization: Bearer <access_token>
```

**응답 스키마**:
```json
{
  "id": 1,
  "username": "myuser",
  "created_at": "2026-06-09T10:30:00Z"
}
```

**상태 코드**:
- `200 OK`: 정상 응답
- `401 Unauthorized`: 토큰 없음 또는 유효하지 않음
- `403 Forbidden`: 토큰 만료됨

**예제**:
```bash
curl -X GET http://localhost:8000/auth/me \
  -H "Authorization: Bearer eyJ..."
```

---

### 0.5 실시간 시세 스트림 (WebSocket)

```http
WS /ws/prices/{krx_code}
```

**설명**: 지정된 종목의 실시간 시세를 WebSocket으로 스트리밍합니다. 10초 주기로 업데이트됩니다.

**경로 파라미터**:
| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `krx_code` | string | KRX 종목 코드 (예: "005930") |

**연결 성공 메시지**:
```json
{
  "type": "connection_established",
  "krx_code": "005930",
  "timestamp": "2026-06-09T14:30:00Z"
}
```

**시세 업데이트 메시지** (10초마다):
```json
{
  "type": "price_update",
  "krx_code": "005930",
  "name": "삼성전자",
  "current_price": 75000,
  "previous_close": 73000,
  "price_change": 2000,
  "change_rate": 2.74,
  "trading_volume": 15234567,
  "timestamp": "2026-06-09T14:30:10Z"
}
```

**응답 필드**:
| 필드 | 타입 | 설명 |
|------|------|------|
| `type` | string | 메시지 타입 (connection_established, price_update, error, close) |
| `krx_code` | string | KRX 종목 코드 |
| `name` | string | 종목명 |
| `current_price` | number | 현재가 (원) |
| `previous_close` | number | 전일 종가 (원) |
| `price_change` | number | 변동액 (원) |
| `change_rate` | number | 변동률 (%) |
| `trading_volume` | number | 거래량 (주) |
| `timestamp` | string | ISO 8601 타임스탐프 (UTC) |

**오류 메시지**:
```json
{
  "type": "error",
  "krx_code": "005930",
  "error": "종목 코드를 찾을 수 없습니다.",
  "timestamp": "2026-06-09T14:30:00Z"
}
```

**종료 메시지**:
```json
{
  "type": "close",
  "krx_code": "005930",
  "reason": "클라이언트 요청으로 구독 해제",
  "timestamp": "2026-06-09T14:35:00Z"
}
```

**상태 코드**:
- `101 Switching Protocols`: WebSocket 연결 성공
- `400 Bad Request`: 유효하지 않은 종목 코드
- `404 Not Found`: 종목 코드 없음

**예제**:
```javascript
// JavaScript WebSocket 클라이언트
const ws = new WebSocket('ws://localhost:8000/ws/prices/005930');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'price_update') {
    console.log(`${data.name}: ${data.current_price}원 (${data.change_rate}%)`);
  }
};

ws.onclose = () => {
  console.log('연결 종료');
};
```

---

### 1. 알림 관리 (Notifications) — Phase 5 신규

#### 1.1 가격 알림 생성

```http
POST /watchlist/alerts
```

**설명**: 관심 목록의 종목에 대해 가격 알림을 생성합니다. 목표가에 도달하면 텔레그램으로 1회 통지됩니다. (인증 필수)

**요청 본문**:
```json
{
  "krx_code": "005930",
  "target_price": 80000,
  "direction": "above"
}
```

**응답 스키마**:
```json
{
  "id": 1,
  "krx_code": "005930",
  "name": "삼성전자",
  "target_price": 80000,
  "direction": "above",
  "is_active": true,
  "triggered_at": null,
  "created_at": "2026-06-09T14:30:00Z"
}
```

**응답 필드**:
| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | integer | 알림 ID |
| `krx_code` | string | KRX 종목 코드 |
| `name` | string | 종목명 |
| `target_price` | number | 목표가 (원) |
| `direction` | string | 방향 (above: 이상, below: 이하) |
| `is_active` | boolean | 활성 상태 |
| `triggered_at` | string or null | 알림 발생 시간 (ISO 8601) |

**상태 코드**:
- `201 Created`: 알림 생성 성공
- `400 Bad Request`: 형식 오류 (예: 유효하지 않은 방향)
- `404 Not Found`: 종목 코드 없음
- `401 Unauthorized`: 인증 필수

**예제**:
```bash
curl -X POST http://localhost:8000/watchlist/alerts \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"krx_code": "005930", "target_price": 80000, "direction": "above"}'
```

---

#### 1.2 가격 알림 목록 조회

```http
GET /watchlist/alerts
```

**설명**: 현재 사용자의 모든 활성/비활성 가격 알림을 조회합니다. (인증 필수)

**요청 헤더**:
```
Authorization: Bearer <access_token>
```

**응답 스키마**:
```json
{
  "alerts": [
    {
      "id": 1,
      "krx_code": "005930",
      "name": "삼성전자",
      "target_price": 80000,
      "direction": "above",
      "is_active": true,
      "triggered_at": null,
      "created_at": "2026-06-09T14:30:00Z"
    },
    {
      "id": 2,
      "krx_code": "000660",
      "name": "SK하이닉스",
      "target_price": 100000,
      "direction": "below",
      "is_active": false,
      "triggered_at": "2026-06-09T15:00:00Z",
      "created_at": "2026-06-08T10:00:00Z"
    }
  ],
  "count": 2
}
```

**상태 코드**:
- `200 OK`: 정상 응답
- `401 Unauthorized`: 인증 필수

**예제**:
```bash
curl -X GET http://localhost:8000/watchlist/alerts \
  -H "Authorization: Bearer eyJ..."
```

---

#### 1.3 가격 알림 삭제

```http
DELETE /watchlist/alerts/{id}
```

**설명**: 가격 알림을 삭제합니다. (인증 필수)

**경로 파라미터**:
| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `id` | integer | 알림 ID |

**상태 코드**:
- `204 No Content`: 삭제 성공
- `404 Not Found`: 알림 없음 또는 다른 사용자의 알림
- `401 Unauthorized`: 인증 필수

**예제**:
```bash
curl -X DELETE http://localhost:8000/watchlist/alerts/1 \
  -H "Authorization: Bearer eyJ..."
```

---

#### 1.4 이메일 구독 신청

```http
POST /notifications/email
```

**설명**: 사용자의 이메일 주소를 등록하여 알림을 구독합니다. SMTP를 통해 가격 알림 및 주간 요약을 받습니다. (인증 필수)

**요청 본문**:
```json
{
  "email": "user@example.com"
}
```

**응답 스키마**:
```json
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true,
  "created_at": "2026-06-09T14:30:00Z"
}
```

**응답 필드**:
| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | integer | 구독 ID |
| `email` | string | 이메일 주소 |
| `is_active` | boolean | 구독 활성 상태 |
| `created_at` | string | 구독 생성 시간 (ISO 8601) |

**상태 코드**:
- `201 Created`: 구독 성공
- `422 Unprocessable Entity`: 유효하지 않은 이메일 형식
- `400 Bad Request`: 이미 구독 중 또는 형식 오류
- `401 Unauthorized`: 인증 필수

**예제**:
```bash
curl -X POST http://localhost:8000/notifications/email \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

---

#### 1.5 이메일 구독 해지

```http
DELETE /notifications/email
```

**설명**: 이메일 구독을 해지합니다. (인증 필수)

**요청 헤더**:
```
Authorization: Bearer <access_token>
```

**응답 스키마**:
```json
{
  "message": "구독이 해지되었습니다.",
  "email": "user@example.com"
}
```

**상태 코드**:
- `200 OK`: 구독 해지 성공
- `404 Not Found`: 구독 정보 없음
- `401 Unauthorized`: 인증 필수

**예제**:
```bash
curl -X DELETE http://localhost:8000/notifications/email \
  -H "Authorization: Bearer eyJ..."
```

---

### 2. 관심 목록 (Watchlist)

#### 1.1 관심 목록 조회

```http
GET /watchlist
```

**설명**: 현재 사용자의 관심 목록을 조회합니다. (인증 필수)

**요청 헤더**:
```
Authorization: Bearer <access_token>
```

**응답 스키마**:
```json
{
  "watchlist": [
    {
      "krx_code": "005930",
      "name": "삼성전자",
      "sector": "전자",
      "current_price": 75000,
      "price_change_rate": 2.74,
      "added_at": "2026-06-09T10:30:00Z"
    },
    {
      "krx_code": "000660",
      "name": "SK하이닉스",
      "sector": "전자",
      "current_price": 120000,
      "price_change_rate": 1.25,
      "added_at": "2026-06-09T11:00:00Z"
    }
  ],
  "count": 2
}
```

**상태 코드**:
- `200 OK`: 정상 응답
- `401 Unauthorized`: 인증 필수

**예제**:
```bash
curl -X GET http://localhost:8000/watchlist \
  -H "Authorization: Bearer eyJ..."
```

---

#### 1.2 관심 목록에 종목 추가

```http
POST /watchlist
```

**설명**: 관심 목록에 종목을 추가합니다. 중복 추가는 자동 방지됩니다. (인증 필수)

**요청 본문**:
```json
{
  "krx_code": "005930"
}
```

**응답 스키마**:
```json
{
  "krx_code": "005930",
  "name": "삼성전자",
  "sector": "전자",
  "current_price": 75000,
  "price_change_rate": 2.74,
  "added_at": "2026-06-09T10:30:00Z"
}
```

**상태 코드**:
- `201 Created`: 추가 성공
- `400 Bad Request`: 이미 추가됨 또는 형식 오류
- `404 Not Found`: 종목 코드 없음
- `401 Unauthorized`: 인증 필수

**예제**:
```bash
curl -X POST http://localhost:8000/watchlist \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"krx_code": "005930"}'
```

---

#### 1.3 관심 목록에서 종목 삭제

```http
DELETE /watchlist/{krx_code}
```

**설명**: 관심 목록에서 종목을 삭제합니다. (인증 필수)

**경로 파라미터**:
| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `krx_code` | string | KRX 종목 코드 |

**상태 코드**:
- `200 OK`: 삭제 성공
- `404 Not Found`: 해당 종목이 관심 목록에 없음
- `401 Unauthorized`: 인증 필수

**예제**:
```bash
curl -X DELETE http://localhost:8000/watchlist/005930 \
  -H "Authorization: Bearer eyJ..."
```

---

### 3. 추천 리스트 조회

#### 3.1 Top 10 주식 추천

```http
GET /recommendations
```

**설명**: 당일 최상위 10개 종목의 추천 리스트를 반환합니다. 결과는 Redis에 캐시되며, 캐시 히트 시 500ms 이내에 응답합니다.

**응답 스키마**:
```json
{
  "stocks": [
    {
      "rank": 1,
      "krx_code": "005930",
      "name": "삼성전자",
      "sector": "전자",
      "score": 0.87,
      "sentiment_score": 0.75,
      "volume_score": 0.92,
      "momentum_score": 0.85,
      "anomaly_score": 0.88,
      "current_price": 75000,
      "price_change_rate": 2.5,
      "trading_volume": 15234567,
      "news_count": 12,
      "reason": "긍정적 뉴스 12건, 거래량 이상 신호 감지, 상승 모멘텀 강함"
    },
    ...
  ],
  "metadata": {
    "timestamp": "2026-06-01T14:30:00Z",
    "last_update": "2026-06-01T14:30:00Z",
    "status": "ready",
    "cache_hit": true,
    "etf_count": 3
  }
}
```

**응답 필드**:
| 필드 | 타입 | 설명 |
|------|------|------|
| `rank` | integer | 순위 (1~10) |
| `krx_code` | string | KRX 종목 코드 |
| `name` | string | 종목명 |
| `sector` | string | 섹터 |
| `score` | number | 종합 점수 (0~1) |
| `sentiment_score` | number | 감성 점수 (0~1) |
| `volume_score` | number | 거래량 점수 (0~1) |
| `momentum_score` | number | 모멘텀 점수 (0~1) |
| `anomaly_score` | number | 거래량 이상 점수 (0~1) |
| `current_price` | number | 현재가 (원) |
| `price_change_rate` | number | 등락률 (%) |
| `trading_volume` | number | 거래량 (주) |
| `news_count` | integer | 관련 뉴스 건수 |
| `reason` | string | 추천 근거 (자연어) |

**상태 코드**:
- `200 OK`: 정상 응답, 추천 데이터 즉시 제공
- `202 Accepted`: 데이터 준비 중, 곧 준비될 예정
- `500 Internal Server Error`: 서버 오류

**오류 응답**:
```json
{
  "detail": "추천 데이터가 아직 준비되지 않았습니다. 잠시 후 다시 시도해주세요.",
  "status": "preparing",
  "last_update": "2026-06-01T09:00:00Z"
}
```

**예제**:
```bash
curl -X GET http://localhost:8000/recommendations
```

---

#### 3.2 종목별 상세 추천 근거

```http
GET /recommendations/{krx_code}
```

**설명**: 특정 종목의 상세한 추천 근거를 반환합니다. 종목을 선택했을 때 모달에 표시할 정보를 제공합니다.

**경로 파라미터**:
| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `krx_code` | string | KRX 종목 코드 (예: "005930") |

**응답 스키마**:
```json
{
  "krx_code": "005930",
  "name": "삼성전자",
  "sector": "전자",
  "current_price": 75000,
  "price_change_rate": 2.5,
  "trading_volume": 15234567,
  "recommendation": {
    "rank": 1,
    "score": 0.87,
    "score_breakdown": {
      "sentiment": {
        "score": 0.75,
        "weight": 0.40,
        "contribution": 0.30
      },
      "volume": {
        "score": 0.92,
        "weight": 0.20,
        "contribution": 0.18
      },
      "momentum": {
        "score": 0.85,
        "weight": 0.25,
        "contribution": 0.21
      },
      "anomaly": {
        "score": 0.88,
        "weight": 0.15,
        "contribution": 0.13
      }
    }
  },
  "contributing_news": [
    {
      "article_id": "news_001",
      "title": "삼성전자, 신제품 출시 계획 발표",
      "summary": "차기 세대 반도체 기술 발표로 업계 주목",
      "sentiment": "positive",
      "sector_tags": ["전자", "반도체"],
      "published_at": "2026-06-01T10:30:00Z",
      "source": "한국경제",
      "url": "https://example.com/article/001",
      "impact_score": 0.92
    },
    ...
  ],
  "sector_trend": {
    "sector": "전자",
    "trend_score": 0.78,
    "news_volume": 45,
    "avg_sentiment": 0.71,
    "trend_direction": "up",
    "description": "긍정적인 뉴스가 증가하면서 섹터 전체 상승"
  },
  "risk_factors": [
    "최근 부정적 뉴스 2건 감지",
    "거래량 변동성 높음"
  ]
}
```

**응답 필드**:
| 필드 | 타입 | 설명 |
|------|------|------|
| `score_breakdown` | object | 점수 구성 상세 (감성, 거래량, 모멘텀, 이상거래량) |
| `contributing_news` | array | 기여한 주요 뉴스 (최대 5건) |
| `impact_score` | number | 개별 뉴스의 점수 영향도 (0~1) |
| `sector_trend` | object | 관련 섹터의 트렌드 정보 |
| `risk_factors` | array | 위험 요인 (선택적) |

**상태 코드**:
- `200 OK`: 정상 응답
- `404 Not Found`: 해당 종목 코드 없음
- `500 Internal Server Error`: 서버 오류

**오류 응답**:
```json
{
  "detail": "종목 코드 '999999'를 찾을 수 없습니다.",
  "krx_code": "999999"
}
```

**예제**:
```bash
curl -X GET http://localhost:8000/recommendations/005930
```

---

### 4. 포트폴리오 관리 (Portfolio)

#### 4.1 포트폴리오 목록 조회

```http
GET /portfolios
```

**설명**: 현재 사용자의 모든 포트폴리오를 조회합니다. (인증 필수)

**요청 헤더**:
```
Authorization: Bearer <access_token>
```

**응답 스키마**:
```json
{
  "portfolios": [
    {
      "id": 1,
      "user_id": 1,
      "name": "주식 포트폴리오",
      "description": "장기 투자용",
      "total_value": 5000000,
      "total_investment": 4500000,
      "return_rate": 11.11,
      "created_at": "2026-06-09T10:30:00Z"
    },
    ...
  ]
}
```

**상태 코드**:
- `200 OK`: 정상 응답
- `401 Unauthorized`: 인증 필수

**예제**:
```bash
curl -X GET http://localhost:8000/portfolios \
  -H "Authorization: Bearer eyJ..."
```

---

#### 4.2 포트폴리오 생성

```http
POST /portfolios
```

**설명**: 새로운 포트폴리오를 생성합니다. (인증 필수)

**요청 본문**:
```json
{
  "name": "주식 포트폴리오",
  "description": "장기 투자용"
}
```

**응답 스키마**:
```json
{
  "id": 1,
  "user_id": 1,
  "name": "주식 포트폴리오",
  "description": "장기 투자용",
  "total_value": 0,
  "total_investment": 0,
  "return_rate": 0,
  "created_at": "2026-06-09T10:30:00Z"
}
```

**상태 코드**:
- `201 Created`: 포트폴리오 생성 성공
- `400 Bad Request`: 형식 오류
- `401 Unauthorized`: 인증 필수

**예제**:
```bash
curl -X POST http://localhost:8000/portfolios \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"name": "주식 포트폴리오", "description": "장기 투자용"}'
```

---

#### 4.3 보유 종목 추가

```http
POST /portfolios/{portfolio_id}/holdings
```

**설명**: 포트폴리오에 종목을 추가합니다. (인증 필수)

**경로 파라미터**:
| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `portfolio_id` | integer | 포트폴리오 ID |

**요청 본문**:
```json
{
  "krx_code": "005930",
  "quantity": 10,
  "purchase_price": 75000,
  "purchase_date": "2026-06-01"
}
```

**응답 스키마**:
```json
{
  "id": 1,
  "portfolio_id": 1,
  "krx_code": "005930",
  "name": "삼성전자",
  "quantity": 10,
  "purchase_price": 75000,
  "current_price": 76000,
  "current_value": 760000,
  "return_amount": 10000,
  "return_rate": 1.33,
  "purchase_date": "2026-06-01"
}
```

**상태 코드**:
- `201 Created`: 종목 추가 성공
- `400 Bad Request`: 형식 오류
- `404 Not Found`: 포트폴리오 없음
- `401 Unauthorized`: 인증 필수

**예제**:
```bash
curl -X POST http://localhost:8000/portfolios/1/holdings \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{"krx_code": "005930", "quantity": 10, "purchase_price": 75000, "purchase_date": "2026-06-01"}'
```

---

#### 4.4 포트폴리오 성과 분석

```http
GET /portfolios/{portfolio_id}/performance
```

**설명**: 포트폴리오의 전체 성과를 분석합니다. (인증 필수)

**경로 파라미터**:
| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `portfolio_id` | integer | 포트폴리오 ID |

**응답 스키마**:
```json
{
  "portfolio_id": 1,
  "total_investment": 750000,
  "total_value": 760000,
  "total_return_amount": 10000,
  "total_return_rate": 1.33,
  "holdings_count": 1,
  "holdings": [
    {
      "krx_code": "005930",
      "name": "삼성전자",
      "quantity": 10,
      "purchase_price": 75000,
      "current_price": 76000,
      "current_value": 760000,
      "return_amount": 10000,
      "return_rate": 1.33,
      "weight": 100.0
    }
  ],
  "last_updated": "2026-06-09T14:30:00Z"
}
```

**상태 코드**:
- `200 OK`: 정상 응답
- `404 Not Found`: 포트폴리오 없음
- `401 Unauthorized`: 인증 필수

**예제**:
```bash
curl -X GET http://localhost:8000/portfolios/1/performance \
  -H "Authorization: Bearer eyJ..."
```

#### 4.5 포트폴리오 AI 분석

```http
POST /portfolios/{portfolio_id}/ai-analysis
```

**설명**: Claude haiku-4-5 모델을 사용하여 포트폴리오를 AI로 분석합니다. (인증 필수)

**경로 파라미터**:
| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `portfolio_id` | integer | 포트폴리오 ID |

**요청 헤더**:
```
Authorization: Bearer <access_token>
```

**응답 스키마**:
```json
{
  "portfolio_id": 1,
  "portfolio_name": "주식 포트폴리오",
  "analysis": {
    "summary": "현재 포트폴리오는 기술주 중심의 구성으로 높은 성장성을 기대할 수 있습니다.",
    "composition_analysis": "전자 섹터(60%), 금융(25%), 화학(15%)으로 구성되어 있으며, 기술주 비중이 높습니다.",
    "risk_assessment": "동일 섹터 집중 위험이 존재하며, 최대 낙폭 위험을 고려한 분산 필요",
    "recommendations": [
      "전자 섹터 비중을 50% 이하로 감소 검토",
      "경기방어주(유틸리티, 소비재) 추가 고려",
      "장기 보유 자산에 대한 분할 매매 전략 수립"
    ],
    "investment_strategy": "중장기 성장 전략으로 현재 구성은 적절하나, 시장 변동성에 대비한 헤징 필요"
  },
  "disclaimer": "본 분석은 정보 제공 목적이며 투자 권유가 아닙니다. 과거 성과가 미래를 보장하지 않으며, 투자 손실에 대한 책임은 사용자에게 있습니다. 전문가 상담을 권장합니다.",
  "analyzed_at": "2026-06-09T14:30:00Z"
}
```

**응답 필드**:
| 필드 | 타입 | 설명 |
|------|------|------|
| `portfolio_id` | integer | 포트폴리오 ID |
| `portfolio_name` | string | 포트폴리오 이름 |
| `analysis` | object | AI 분석 결과 |
| `summary` | string | 포트폴리오 요약 평가 |
| `composition_analysis` | string | 구성 분석 |
| `risk_assessment` | string | 리스크 평가 |
| `recommendations` | array | 개선 권고사항 |
| `investment_strategy` | string | 투자 전략 제안 |
| `disclaimer` | string | 투자 책임 면책 고지 |
| `analyzed_at` | string | 분석 시간 (ISO 8601) |

**상태 코드**:
- `200 OK`: 분석 성공
- `404 Not Found`: 포트폴리오 없음
- `401 Unauthorized`: 인증 필수 또는 다른 사용자의 포트폴리오
- `500 Internal Server Error`: Claude API 오류

**오류 응답**:
```json
{
  "detail": "Claude API 호출 실패: API 키 검증 오류",
  "status": "error"
}
```

**예제**:
```bash
curl -X POST http://localhost:8000/portfolios/1/ai-analysis \
  -H "Authorization: Bearer eyJ..."
```

---

### 5. 백테스팅 (Backtesting)

#### 5.1 백테스트 실행

```http
POST /backtest/run
```

**설명**: 특정 전략으로 백테스트를 실행합니다. (인증 필수)

**요청 본문**:
```json
{
  "strategy": "momentum",
  "krx_codes": ["005930", "000660", "035420"],
  "start_date": "2025-06-01",
  "end_date": "2026-06-01",
  "initial_capital": 1000000
}
```

**응답 스키마**:
```json
{
  "id": 1,
  "user_id": 1,
  "strategy": "momentum",
  "start_date": "2025-06-01",
  "end_date": "2026-06-01",
  "initial_capital": 1000000,
  "status": "running",
  "created_at": "2026-06-09T14:30:00Z"
}
```

**상태 코드**:
- `202 Accepted`: 백테스트 시작 (비동기 처리)
- `400 Bad Request`: 형식 오류 또는 유효하지 않은 전략
- `401 Unauthorized`: 인증 필수

**예제**:
```bash
curl -X POST http://localhost:8000/backtest/run \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": "momentum",
    "krx_codes": ["005930", "000660"],
    "start_date": "2025-06-01",
    "end_date": "2026-06-01",
    "initial_capital": 1000000
  }'
```

---

#### 5.2 백테스트 결과 조회

```http
GET /backtest/runs/{backtest_id}
```

**설명**: 개별 백테스트의 최종 결과를 조회합니다.

**경로 파라미터**:
| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `backtest_id` | integer | 백테스트 ID |

**응답 스키마**:
```json
{
  "id": 1,
  "user_id": 1,
  "strategy": "momentum",
  "start_date": "2025-06-01",
  "end_date": "2026-06-01",
  "initial_capital": 1000000,
  "final_value": 1250000,
  "total_return": 250000,
  "return_rate": 25.0,
  "cagr": 22.5,
  "max_drawdown": -15.3,
  "sharpe_ratio": 1.85,
  "status": "completed",
  "created_at": "2026-06-09T14:30:00Z",
  "completed_at": "2026-06-09T14:45:00Z"
}
```

**응답 필드**:
| 필드 | 타입 | 설명 |
|------|------|------|
| `cagr` | number | 연복합 성장률 (%) |
| `max_drawdown` | number | 최대 낙폭 (%) |
| `sharpe_ratio` | number | 샤프 지수 |
| `status` | string | 상태 (running/completed/failed) |

**상태 코드**:
- `200 OK`: 정상 응답 (완료됨)
- `202 Accepted`: 진행 중
- `404 Not Found`: 백테스트 없음

**예제**:
```bash
curl -X GET http://localhost:8000/backtest/runs/1
```

---

#### 5.3 백테스트 일별 결과

```http
GET /backtest/runs/{backtest_id}/results
```

**설명**: 백테스트의 일별 상세 결과를 조회합니다.

**경로 파라미터**:
| 파라미터 | 타입 | 설명 |
|---------|------|------|
| `backtest_id` | integer | 백테스트 ID |

**응답 스키마**:
```json
{
  "backtest_id": 1,
  "daily_results": [
    {
      "date": "2025-06-01",
      "portfolio_value": 1000000,
      "cash": 100000,
      "holdings_value": 900000,
      "return_rate": 0.0,
      "positions": [
        {
          "krx_code": "005930",
          "quantity": 10,
          "price": 75000,
          "value": 750000
        }
      ]
    },
    {
      "date": "2025-06-02",
      "portfolio_value": 1025000,
      "cash": 100000,
      "holdings_value": 925000,
      "return_rate": 2.5,
      "positions": [...]
    },
    ...
  ],
  "total_days": 252
}
```

**상태 코드**:
- `200 OK`: 정상 응답
- `404 Not Found`: 백테스트 없음 또는 결과 없음

**예제**:
```bash
curl -X GET http://localhost:8000/backtest/runs/1/results
```

---

### 6. 텔레그램 알림 (Telegram)

#### 6.1 구독 시작

```http
POST /telegram/subscribe
```

**설명**: 텔레그램 봇에서 사용자를 구독합니다.

**요청 본문**:
```json
{
  "chat_id": 123456789,
  "user_id": 1
}
```

**응답 스키마**:
```json
{
  "id": 1,
  "chat_id": 123456789,
  "user_id": 1,
  "is_active": true,
  "subscribed_at": "2026-06-09T14:30:00Z"
}
```

**상태 코드**:
- `201 Created`: 구독 성공
- `400 Bad Request`: 이미 구독 중이거나 형식 오류

**예제**:
```bash
curl -X POST http://localhost:8000/telegram/subscribe \
  -H "Content-Type: application/json" \
  -d '{"chat_id": 123456789, "user_id": 1}'
```

---

#### 6.2 구독 취소

```http
POST /telegram/unsubscribe
```

**설명**: 텔레그램 구독을 취소합니다.

**요청 본문**:
```json
{
  "chat_id": 123456789
}
```

**상태 코드**:
- `200 OK`: 구독 취소 성공
- `404 Not Found`: 구독 정보 없음

---

### 7. 뉴스 정보

#### 7.1 분석 완료 뉴스 피드

```http
GET /news?limit=N&offset=O
```

**설명**: 감성 분석이 완료된 최신 뉴스 피드를 반환합니다. 페이지네이션을 지원합니다.

**쿼리 파라미터**:
| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|-------|------|
| `limit` | integer | 10 | 반환할 뉴스 건수 (최대 100) |
| `offset` | integer | 0 | 건너뛸 뉴스 건수 |
| `sentiment` | string | - | 감성 필터 (positive/negative/neutral) |
| `sector` | string | - | 섹터 필터 |

**응답 스키마**:
```json
{
  "news": [
    {
      "article_id": "news_001",
      "title": "삼성전자, 신제품 출시 계획 발표",
      "summary": "차기 세대 반도체 기술 발표로 업계 주목",
      "content": "삼성전자가 어제 기술 발표회에서...",
      "sentiment": "positive",
      "sentiment_score": 0.92,
      "sectors": ["전자", "반도체"],
      "keywords": ["삼성전자", "반도체", "신제품"],
      "mentioned_stocks": [
        {
          "krx_code": "005930",
          "name": "삼성전자"
        }
      ],
      "source": "한국경제",
      "published_at": "2026-06-01T10:30:00Z",
      "collected_at": "2026-06-01T10:45:00Z",
      "url": "https://example.com/article/001"
    },
    ...
  ],
  "metadata": {
    "total": 234,
    "limit": 10,
    "offset": 0,
    "page": 1,
    "pages": 24
  }
}
```

**응답 필드**:
| 필드 | 타입 | 설명 |
|------|------|------|
| `sentiment` | string | 감성 (positive/negative/neutral) |
| `sentiment_score` | number | 감성 점수 (0~1) |
| `sectors` | array | 관련 섹터 태그 |
| `keywords` | array | 핵심 키워드 |
| `mentioned_stocks` | array | 기사에서 언급된 종목 |

**상태 코드**:
- `200 OK`: 정상 응답
- `400 Bad Request`: 잘못된 쿼리 파라미터
- `500 Internal Server Error`: 서버 오류

**예제**:
```bash
# 기본 요청
curl -X GET http://localhost:8000/news?limit=20

# 긍정 감성만 필터
curl -X GET http://localhost:8000/news?sentiment=positive&limit=10

# 전자 섹터 뉴스만
curl -X GET http://localhost:8000/news?sector=전자&limit=10
```

---

### 8. 섹터 트렌드

#### 8.1 섹터별 트렌드 시계열

```http
GET /sectors/trends?days=N
```

**설명**: 지난 N일간의 섹터별 트렌드 스코어를 시계열로 반환합니다. 차트 그리기에 사용됩니다.

**쿼리 파라미터**:
| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|-------|------|
| `days` | integer | 7 | 조회 기간 (일) |

**응답 스키마**:
```json
{
  "trends": [
    {
      "timestamp": "2026-06-01T00:00:00Z",
      "sectors": [
        {
          "sector": "전자",
          "score": 0.78,
          "sentiment_score": 0.71,
          "volume_score": 0.85,
          "news_count": 45,
          "avg_sentiment": 0.71,
          "direction": "up"
        },
        {
          "sector": "금융",
          "score": 0.62,
          "sentiment_score": 0.55,
          "volume_score": 0.68,
          "news_count": 28,
          "avg_sentiment": 0.55,
          "direction": "down"
        },
        ...
      ]
    },
    ...
  ],
  "metadata": {
    "start_date": "2026-05-25",
    "end_date": "2026-06-01",
    "days": 7,
    "sectors_count": 12,
    "data_points": 7
  }
}
```

**응답 필드**:
| 필드 | 타입 | 설명 |
|------|------|------|
| `score` | number | 섹터 트렌드 점수 (0~1) |
| `sentiment_score` | number | 평균 감성 점수 (0~1) |
| `volume_score` | number | 거래량 정규화 점수 (0~1) |
| `news_count` | integer | 해당 섹터 뉴스 건수 |
| `direction` | string | 트렌드 방향 (up/down/stable) |

**상태 코드**:
- `200 OK`: 정상 응답
- `400 Bad Request`: 잘못된 days 값
- `500 Internal Server Error`: 서버 오류

**예제**:
```bash
# 최근 7일 트렌드
curl -X GET http://localhost:8000/sectors/trends?days=7

# 최근 30일 트렌드
curl -X GET http://localhost:8000/sectors/trends?days=30
```

---

### 9. 헬스 체크

#### 9.1 시스템 상태 확인

```http
GET /health
```

**설명**: 시스템의 전반적인 건강 상태를 확인합니다. 데이터베이스, Redis, Claude API 상태를 포함합니다.

**응답 스키마**:
```json
{
  "status": "healthy",
  "timestamp": "2026-06-01T14:30:00Z",
  "components": {
    "database": {
      "status": "connected",
      "latency_ms": 12
    },
    "redis": {
      "status": "connected",
      "latency_ms": 5
    },
    "claude_api": {
      "status": "available",
      "last_check": "2026-06-01T14:00:00Z"
    }
  },
  "scheduler": {
    "status": "running",
    "last_collection": "2026-06-01T12:30:00Z",
    "next_collection": "2026-06-02T06:00:00Z",
    "last_analysis": "2026-06-01T12:45:00Z"
  },
  "data": {
    "total_articles": 12345,
    "analyzed_articles": 10234,
    "recommendations_ready": true,
    "cache_size_mb": 125
  }
}
```

**응답 필드**:
| 필드 | 타입 | 설명 |
|------|------|------|
| `status` | string | 전체 상태 (healthy/degraded/unhealthy) |
| `components` | object | 각 컴포넌트별 상태 |
| `scheduler` | object | 스케줄러 상태 |
| `data` | object | 데이터 통계 |

**상태 코드**:
- `200 OK`: 정상 (healthy 또는 degraded)
- `503 Service Unavailable`: 서비스 불가 (unhealthy)

**예제**:
```bash
curl -X GET http://localhost:8000/health
```

---

---

## 오류 처리

모든 오류 응답은 다음 형식을 따릅니다:

```json
{
  "detail": "오류 메시지",
  "status_code": 400,
  "timestamp": "2026-06-01T14:30:00Z"
}
```

### 공통 오류 코드

| 코드 | 설명 |
|------|------|
| `400 Bad Request` | 잘못된 쿼리 파라미터 또는 요청 본문 |
| `404 Not Found` | 요청한 리소스 없음 |
| `500 Internal Server Error` | 서버 오류 |
| `503 Service Unavailable` | 서비스 일시 불가 (데이터베이스/Redis 연결 오류) |

---

## 캐싱 전략

### 응답 캐싱

```
GET /recommendations
└─ Cache: 1시간 (최대)
└─ CDN: 5분
└─ 사용자 에이전트: 최대 5분
```

### 캐시 헤더

모든 응답에 포함:
```
Cache-Control: public, max-age=3600
ETag: "abc123def456"
Last-Modified: Wed, 01 Jun 2026 14:30:00 GMT
```

---

## 응답 형식

### 시간 형식

모든 타임스탬프는 ISO 8601 형식 (UTC):
```
2026-06-01T14:30:00Z
```

### 숫자 형식

- 점수: 0~1 범위의 소수 (최대 2자리)
- 가격: 정수 (원)
- 변동률: 소수 (최대 2자리, %)

---

## 투자 책임 면책 고지

본 API는 **투자 정보 제공 도구**이며 투자 권유, 자문, 또는 투자 판단을 위한 전문적 의견이 아닙니다.

- 과거 뉴스 분석 결과가 미래 주가를 보장하지 않습니다
- API 사용자는 독립적인 투자 판단 책임을 집니다
- API 제공자는 사용으로 인한 손실에 대해 책임을 지지 않습니다
- 실제 투자 전에 전문가 상담을 권장합니다

---

## 속도 제한 (Rate Limiting)

현재 속도 제한 없음 (공개 API). 향후 사용자별 레이트 제한 도입 예정.

---

## 버전 관리

현재 버전: **v1** (기본)

향후 주요 변경이 필요한 경우 새로운 버전 도입 예정.

---

## 지원 및 피드백

문제 발생 시:
1. `/health` 엔드포인트로 시스템 상태 확인
2. 에러 응답의 `detail` 메시지 검토
3. 백엔드 로그 확인: `docker-compose logs backend`
4. 이슈 생성 시 요청/응답, 에러 메시지, 환경 정보 포함
