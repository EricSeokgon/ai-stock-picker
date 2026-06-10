# SPEC-STOCK-009 — 진행 상황 (Progress)

- SPEC: 추천 품질 개선 — 피드백 기반 가중치 + 스코어 투명성
- 상태: draft (Plan 완료, Run 미시작)
- 생성일: 2026-06-10
- 개발 방법론: quality.yaml `development_mode` 따름

---

## 작업 진행표

| TASK | 설명 | 우선순위 | 상태 | 연결 AC |
|------|------|---------|------|---------|
| TASK-001 | 마이그레이션 0012 — recommendations 컬럼(base_score, feedback_score) | High | pending | AC-1 |
| TASK-002 | 피드백 계수 계산 순수 함수 | High | pending | AC-2, AC-3, AC-7 |
| TASK-003 | 피드백 일괄 집계 조회 (N+1 회피) | High | pending | AC-8 |
| TASK-004 | 조정 적용 순수 함수 (0~1 클램프) | High | pending | AC-3, AC-4, AC-11 |
| TASK-005 | 추천 파이프라인에 피드백 조정 통합 | High | pending | AC-4, AC-5, AC-6 |
| TASK-006 | API 스키마 확장 (선택 필드) | High | pending | AC-9, AC-10 |
| TASK-007 | 스코어 분해 데이터 + 상세 응답 포함 | High | pending | AC-9, AC-11 |
| TASK-008 | 단위 테스트 — 계수·조정 순수 함수 | Medium | pending | AC-2, AC-3, AC-7, AC-11 |
| TASK-009 | 통합 테스트 — 파이프라인 + API 하위호환 | Medium | pending | AC-5, AC-6, AC-9, AC-10 |
| TASK-010 | 프론트 스코어 분해 컴포넌트 | Medium | pending | AC-12, AC-13 |
| TASK-011 | 프론트 추천 목록 피드백 반영 표시 | Medium | pending | AC-13, AC-14 |
| TASK-012 | 프론트 단위 테스트 | Medium | pending | AC-12, AC-13, AC-14 |

상태 범례: pending → in_progress → done

---

## 인수 기준 충족 현황

- 충족: 0 / 14
- 미충족: AC-1 ~ AC-14

---

## 반복 로그 (Re-planning Gate 추적용)

| 반복 | 완료 AC 수 | 오류 델타 | 비고 |
|------|-----------|----------|------|
| (Run 시작 후 각 반복 종료 시 기록) | - | - | 초기 상태 |

---

## 메모

- 기존 4요인 산식(`scoring/engine.py`)·API 응답은 하위 호환 유지가 핵심 제약(REQ-NFR-001/002).
- 피드백 데이터(`recommendation_feedback`)는 SPEC-007에서 이미 수집 중 — 본 SPEC은 이를 점수에
  반영하는 첫 SPEC. 클램프·신뢰도 가중으로 영향을 안전하게 제한.
- 점수 조정은 파이프라인 실행 시점(스케줄러) 일괄 적용 — API 호출 시 재계산 없음(캐시 동작 보존).
- 마이그레이션 누적 번호: 0001~0011 다음 0012.
