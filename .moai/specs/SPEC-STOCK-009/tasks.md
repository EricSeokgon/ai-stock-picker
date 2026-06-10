# SPEC-STOCK-009 — 작업 목록 (Tasks)

추천 품질 개선 — 피드백 기반 가중치 + 스코어 투명성. 총 12개 작업(TASK-001~012).
백엔드 → 프론트 순서로 의존성을 정렬했다. 모든 본문은 한국어, 코드·식별자는 영어.

> 규약: 기존 4요인 산식(`scoring/engine.py`)은 변경 금지(REQ-NFR-001). 신규 API 필드는 선택
> (optional)으로 추가(REQ-NFR-002). 신규 외부 서비스 없음(REQ-NFR-003).

---

## 백엔드 — 데이터 모델 & 피드백 계수

### TASK-001: 마이그레이션 0012 — recommendations 컬럼 추가
- **요구사항**: REQ-FW-006, REQ-NFR-002
- **내용**: `recommendations` 테이블에 `base_score`(Numeric(6,3), nullable),
  `feedback_score`(Numeric(6,3), nullable) 컬럼을 추가하는 Alembic 마이그레이션 0012 작성.
  `total_score`는 그대로 두되 의미를 조정 점수로 사용한다. ORM 모델(`db/models.py`
  `Recommendation`)에도 두 컬럼을 nullable로 추가.
- **수용 연결**: AC-1
- **파일(예상)**: `backend/alembic/versions/0012_recommendation_feedback_score.py`,
  `backend/src/stock_picker/db/models.py`

### TASK-002: 피드백 계수 계산 순수 함수
- **요구사항**: REQ-FW-001, REQ-FW-002, REQ-FW-005
- **내용**: up/down 투표 수를 입력받아 정규화된 피드백 계수를 산출하는 순수 함수 구현.
  표본 수 기반 신뢰도 가중을 적용하고 결과를 `[-MAX_ADJ, +MAX_ADJ]`로 클램프. 투표 0건이면
  0 반환. `MAX_ADJ` 등 상수는 모듈 상단에 명시.
- **수용 연결**: AC-2, AC-3, AC-7
- **파일(예상)**: `backend/src/stock_picker/feedback/weighting.py`

### TASK-003: 피드백 일괄 집계 조회
- **요구사항**: REQ-FW-007
- **내용**: 여러 `krx_code`의 up/down 합계를 단일 쿼리로 조회하여
  `{krx_code: {"up": int, "down": int}}` 형태로 반환하는 함수 구현(GROUP BY 활용).
  종목 수에 비례한 개별 쿼리(N+1) 금지.
- **수용 연결**: AC-8
- **파일(예상)**: `backend/src/stock_picker/feedback/service.py`

### TASK-004: 조정 적용 순수 함수
- **요구사항**: REQ-FW-004, REQ-NFR-001
- **내용**: 기본 점수와 피드백 계수를 받아 조정 점수를 반환하는 순수 함수 구현.
  결과를 0.0~1.0으로 클램프. 기존 `calculate_stock_score`는 호출만 하고 수정하지 않는다
  (조정은 별도 단계). 기본 점수에 대한 조정량(delta)도 함께 계산 가능하도록 설계.
- **수용 연결**: AC-3, AC-4, AC-11
- **파일(예상)**: `backend/src/stock_picker/scoring/engine.py`(신규 함수 추가) 또는
  `backend/src/stock_picker/feedback/weighting.py`

---

## 백엔드 — 파이프라인 통합 & API

### TASK-005: 추천 파이프라인에 피드백 조정 통합
- **요구사항**: REQ-FW-003, REQ-FW-006
- **내용**: `RecommendationService.run()`에서 후보 종목들의 기본 점수 계산 직후 TASK-003의
  일괄 집계 + TASK-002 계수 + TASK-004 조정을 적용. 조정 점수로 `rank_stocks` 수행.
  저장 시 `base_score`, `feedback_score`, `total_score`(=조정 점수)를 함께 기록.
- **수용 연결**: AC-4, AC-5, AC-6
- **파일(예상)**: `backend/src/stock_picker/recommendation/service.py`

### TASK-006: API 스키마 확장
- **요구사항**: REQ-ST-001, REQ-ST-005, REQ-NFR-002
- **내용**: `RecommendationItem`, `RecommendationDetailResponse`에 `base_score`,
  `feedback_score`를 선택(optional) 필드로 추가. 라우터에서 신규 컬럼을 안전하게 노출
  (구 데이터 None 허용). 기존 필드·기본 동작 불변.
- **수용 연결**: AC-9, AC-10
- **파일(예상)**: `backend/src/stock_picker/api/schemas.py`,
  `backend/src/stock_picker/api/routes/recommendations.py`

### TASK-007: 스코어 분해 데이터 계산 + 상세 응답 포함
- **요구사항**: REQ-ST-001, REQ-ST-002
- **내용**: 4요인 가중 기여도(가중치 × 요인 점수)와 피드백 조정량을 계산하는 유틸 구현 후
  `GET /recommendations/{krx_code}` 상세 응답에 분해 데이터(요인별 기여도 목록 + 피드백 조정량)를
  선택 필드로 포함. 기여도 합 = 기본 점수, 기본 점수 + 조정량 = 조정 점수 일관성 보장.
- **수용 연결**: AC-9, AC-11
- **파일(예상)**: `backend/src/stock_picker/scoring/engine.py` 또는 신규 유틸,
  `backend/src/stock_picker/api/schemas.py`,
  `backend/src/stock_picker/api/routes/recommendations.py`

---

## 백엔드 — 테스트

### TASK-008: 단위 테스트 — 계수·조정 순수 함수
- **요구사항**: REQ-FW-001, REQ-FW-002, REQ-FW-004, REQ-FW-005, REQ-NFR-004
- **내용**: 피드백 계수(클램프 경계, 신뢰도 가중, 투표 0건=0), 조정 적용(0~1 클램프,
  base+delta=adjusted), 분해 산술 일관성을 검증하는 단위 테스트. 경계·엣지 케이스 포함.
- **수용 연결**: AC-2, AC-3, AC-7, AC-11
- **파일(예상)**: `backend/tests/unit/test_feedback_weighting.py`,
  `backend/tests/unit/test_score_adjustment.py`

### TASK-009: 통합 테스트 — 파이프라인 반영 + API 하위호환
- **요구사항**: REQ-FW-003, REQ-FW-006, REQ-NFR-002
- **내용**: 피드백이 있는 종목의 조정 점수가 기본과 달라지고 없는 종목은 동일함을 파이프라인
  레벨에서 검증. 상세/목록 API가 `base_score`·`feedback_score`를 노출하고, 구 데이터에서도
  기존 필드만으로 정상 응답함을 검증.
- **수용 연결**: AC-5, AC-6, AC-9, AC-10
- **파일(예상)**: `backend/tests/integration/test_recommendation_feedback_weighting.py`

---

## 프론트엔드 — 스코어 투명성 UI

### TASK-010: 스코어 분해 컴포넌트
- **요구사항**: REQ-ST-003, REQ-ST-005
- **내용**: 요인별 가중 기여도를 막대(또는 동등 시각 요소)로 표시하고 피드백 조정량을 별도로
  표시하는 React 컴포넌트 구현. `StockDetail`/상세 페이지에 통합. 분해 데이터가 없으면 피드백
  영역을 생략하고 오류 없이 렌더링.
- **수용 연결**: AC-12, AC-13
- **파일(예상)**: `frontend/src/components/ScoreBreakdown.tsx`,
  `frontend/src/components/StockDetail.tsx` 또는 `frontend/src/pages/StockDetailPage.tsx`,
  `frontend/src/types.ts`

### TASK-011: 추천 목록 피드백 반영 표시
- **요구사항**: REQ-ST-004, REQ-ST-005
- **내용**: 추천 항목에 피드백 조정이 적용된 경우 배지/툴팁으로 표시하고, base 대비 adjusted
  차이를 인지할 수 있게 한다. `base_score`/`feedback_score`가 없으면 표시를 생략.
- **수용 연결**: AC-13, AC-14
- **파일(예상)**: `frontend/src/components/RecommendationList.tsx`,
  `frontend/src/types.ts`

### TASK-012: 프론트 단위 테스트
- **요구사항**: REQ-ST-003, REQ-ST-004, REQ-ST-005
- **내용**: 분해 컴포넌트 렌더(요인 기여도·피드백 조정 표시), 목록 피드백 배지 표시,
  필드 부재 시(구 데이터) graceful 렌더를 검증하는 테스트.
- **수용 연결**: AC-12, AC-13, AC-14
- **파일(예상)**: `frontend/src/components/__tests__/ScoreBreakdown.test.tsx`,
  `frontend/src/components/__tests__/RecommendationList.test.tsx`

---

## 의존성 그래프

```
TASK-001 ─┬─ TASK-005 ── TASK-009
TASK-002 ─┤              │
TASK-003 ─┤              │
TASK-004 ─┘              │
TASK-006 ── TASK-007 ────┤
TASK-008 (TASK-002/004 후)
TASK-006/007 ── TASK-010 ── TASK-012
            └── TASK-011 ──┘
```

- 우선순위 High: TASK-001~005 (피드백 가중치 코어)
- 우선순위 High: TASK-006~007 (투명성 데이터)
- 우선순위 Medium: TASK-008~009 (테스트), TASK-010~011 (UI)
- 우선순위 Medium: TASK-012 (프론트 테스트)
