# SPEC-STOCK-036 Progress

## Status: COMPLETE

Implementation of portfolio alert system extension supporting 2 new alert types:
1. `portfolio_value_below` — Portfolio total value (KRW) falls below threshold
2. `holding_return` — Individual holding's return % crosses threshold (above/below direction)

## Implementation Summary

- **T-001**: DB 마이그레이션 0023 (target_krx_code, condition_direction nullable 컬럼) ✅
- **T-002**: PortfolioAlert 모델 컬럼 확장 ✅
- **T-003**: 순수 함수 2종 (check_portfolio_value_alert, check_holding_return_alert) ✅
- **T-004**: check_all_portfolio_alerts 분기 확장 ✅
- **T-005**: 스키마 확장 (AlertType Literal, AlertEvaluateResult, AlertHistoryItem) ✅
- **T-006**: 엔드포인트 2종 (POST /evaluate, GET /history) ✅
- **T-007**: 프런트엔드 (API 클라이언트, PortfolioAlertPanel) ✅
- **T-008**: 단위 테스트 26개 작성 및 통과 ✅

## Test Results

- **SPEC-036 테스트**: 26/26 pass
- **전체 단위 테스트**: 939 pass (8 pre-existing failures unrelated)

## Key Decisions

- SPEC-031 `portfolio_alerts` 테이블 재사용 (신규 테이블 금지)
- `condition_direction` NULL → "above" 기본값 (하위 호환)
- `notifications` 테이블을 알림 발화 이력으로 재사용 (SPEC-031 멱등 INSERT 패턴 유지)
- 포트폴리오 알림 평가는 스케줄러가 주기적으로 실행 + 즉시 평가 엔드포인트로 on-demand 지원

## Architecture

### New Alert Types

1. **`portfolio_value_below`**
   - Condition: `portfolio_total_value_krw <= condition_value`
   - Parameter: `condition_value` (KRW, float)
   - Usage: 포트폴리오 총 평가액이 일정 금액 이하로 내려가면 알림

2. **`holding_return`**
   - Condition: `holding_return_pct >= condition_value` (above) OR `holding_return_pct <= condition_value` (below)
   - Parameters: `condition_value` (%, float), `condition_direction` ("above"|"below"), `target_krx_code` (특정 종목)
   - Usage: 보유 중인 개별 종목의 수익률이 목표값을 상향/하향 돌파하면 알림

### Database Schema

**portfolio_alerts table** (SPEC-031)
```sql
ALTER TABLE portfolio_alerts ADD COLUMN target_krx_code VARCHAR(20) NULL;
ALTER TABLE portfolio_alerts ADD COLUMN condition_direction VARCHAR(10) NULL;
```

- `target_krx_code`: 개별 종목 알림용 (portfolio_value_below는 NULL)
- `condition_direction`: holding_return용 ("above"|"below"), portfolio_value_below는 NULL

### New Endpoints

**POST /portfolios/{id}/alerts/evaluate**
- Request: (None, GET 파라미터로 alert_type 선택 가능)
- Response: `AlertEvaluateResult` — 평가 결과 + 발화된 알림 목록
- 용도: 사용자가 알림 규칙을 즉시 테스트, 발화 시뮬레이션

**GET /portfolios/{id}/alerts/history**
- Query params: `limit`, `offset`, `alert_type_filter` (선택)
- Response: `{items: [AlertHistoryItem], total, has_more}`
- 용도: 지난 알림 발화 이력 조회

### Integration with Existing System

- **스케줄러**: 기존 10분 주기 `check_alerts` 작업에 포트폴리오 알림 분기 추가
- **알림 채널**: SPEC-031과 동일하게 이메일·텔레그램·인박스 지원
- **권한 검증**: 포트폴리오 소유자만 알림 CRUD 가능

## Migration Details

**Alembic 0023: portfolio_alerts nullable columns**
- `target_krx_code` (VARCHAR 20, nullable) — holding_return 알림용
- `condition_direction` (VARCHAR 10, nullable) — holding_return 알림용 ("above"|"below")
- Existing SPEC-031 rows: 두 컬럼 모두 NULL로 초기화 (하위 호환)

## Testing Coverage

### Backend Tests (26 total)
- `check_portfolio_value_alert`: 평가액 조건 검증 (3가지 케이스)
- `check_holding_return_alert`: 개별 종목 수익률 조건 검증 (4가지 케이스)
- `check_all_portfolio_alerts`: 2종 알림 통합 점검 (2가지 케이스)
- `POST /evaluate` 엔드포인트: 즉시 평가 (2가지 케이스)
- `GET /history` 엔드포인트: 이력 조회 (2가지 케이스)
- 스케줄러 통합: 주기적 점검 (2가지 케이스)
- 권한 검증: 소유자 외 403 (2가지 케이스)
- 채널 발송: 이메일/텔레그램 게이팅 (2가지 케이스)

### Frontend Tests
- PortfolioAlertPanel: 신규 alert_type 라벨 표시
- AlertTypeLabel 컴포넌트: portfolio_value_below, holding_return 스타일
- API 클라이언트: `apiEvaluateAlerts`, `apiGetAlertHistory`

## Non-Goals

- 자동 매매 (영구 제외)
- 종목별 세분화 프리퍼런스 (별도 SPEC)
- 신규 채널 추가 (별도 SPEC)

## Files Modified/Created

**Backend**
- `backend/alembic/versions/0023_portfolio_alerts_036.py` (신규)
- `backend/src/stock_picker/portfolio/portfolio_alerts.py` (수정)
- `backend/src/stock_picker/portfolio/schemas.py` (수정)
- `backend/src/stock_picker/portfolio/router.py` (수정)
- `backend/tests/unit/test_portfolio_alerts_036.py` (신규)

**Frontend**
- `frontend/src/components/PortfolioAlertPanel.js` (수정)
- `frontend/src/components/PortfolioAlertPanel.tsx` (수정)
- `frontend/src/api/portfolio.js` (수정)
- `frontend/src/api/portfolio.ts` (수정)
