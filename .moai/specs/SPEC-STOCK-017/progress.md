# SPEC-STOCK-017 진행 상황 (Progress)

- **SPEC**: SPEC-STOCK-017 사용자 포트폴리오 성과 분석 (Portfolio Performance Analysis)
- **상태(Status)**: SYNC COMPLETE
- **우선순위(Priority)**: Medium
- **최종 업데이트**: 2026-06-12

---

## 마일스톤 (Milestones)

| ID | 마일스톤 | 상태 | 관련 REQ | 비고 |
|----|----------|------|----------|------|
| M1 | 성과 계산 서비스 (수익률 계산 로직) | DONE | REQ-PERF-001·002·005·007·008·009, REQ-NFR-004 | `calculate_performance` 확장 + 가격 소스를 `get_current_price`로 통일 + 섹터 매핑 공용 모듈화 |
| M2 | 성과 API 엔드포인트 | DONE | REQ-PERF-003·006, REQ-PORT-001·002 | 기존 `GET /portfolios/{id}/performance` 응답 확장(분류 라벨·하위호환) |
| M3 | 섹터별 수익률 집계 | DONE | REQ-PERF-004 | 보유 종목 섹터 태그 기반 투자금 가중평균 집계 + `sector_performance`·`classification_summary` 응답 |
| M4 | 프론트 성과 패널 (요약 + 분류 목록) | DONE | REQ-CHART-001·004 | `Portfolio.tsx` 대시보드 패널 + `api/portfolio.ts` 타입 확장 + 응답 키 정합화 |
| M5 | 도넛 차트 (고/일반/저수익 비율) | DONE | REQ-CHART-002·003·005 | `PerformanceDonutChart.tsx`(recharts PieChart/Pie innerRadius) |
| M6 | 테스트 + 품질 게이트 | DONE | REQ-NFR-001·002·003 | `uv run pytest`(커버리지 85%+)·ruff·`npx vitest run`·tsc 빌드 |

---

## 마일스톤 상세

### M1 — 성과 계산 서비스
- [x] 섹터 매핑(`get_sector`·`_SECTOR_MAP`)을 `portfolio/utils.py` 공용 모듈로 추출하고 중복 제거
- [x] `calculate_performance` 가격 소스를 `realtime.price_feed.get_current_price`로 교체
- [x] 현재가 조회 실패 시 `price_unavailable` 처리 + 0 나눗셈 방지
- [x] 보유 종목 없을 때 빈 응답 처리

### M2 — 성과 API 엔드포인트
- [x] 보유 종목별 `classification`(high/normal/low) 부여
- [x] 응답 스키마 확장(기존 필드 보존, 하위호환)
- [x] 소유권 검증·404 유지 확인

### M3 — 섹터별 수익률 집계
- [x] 섹터별 투자금 가중평균 수익률 계산
- [x] `classification_summary`(분류별 종목 수·투자비중) 산출
- [x] `sector_performance`(투자금 내림차순) 응답 추가

### M4 — 프론트 성과 패널
- [x] `api/portfolio.ts` 타입 확장(classification/sector/summary/sector_performance)
- [x] 백엔드 응답 키와 프론트 타입 드리프트 정합화 (`current_value`→`total_current`, `holdings_count`→`holdings.length`)
- [x] 분류 목록 + 섹터 집계 패널 렌더

### M5 — 도넛 차트
- [x] `PerformanceDonutChart.tsx` 신규(recharts PieChart/Pie innerRadius=40)
- [x] 고/일반/저수익 색상 구분 + 호버 툴팁
- [x] 보유 종목 없을 때 안내 표시

### M6 — 테스트 + 품질 게이트
- [x] 백엔드 단위 테스트(분류 경계값 ±5%, 섹터 집계, 가격 실패, 빈 포트폴리오) 15개 통과
- [x] 백엔드 섹터 유틸 테스트 18개 통과
- [x] 프론트 vitest(도넛 렌더, 타입 정합성) 12개 통과, 전체 191개 통과
- [x] `service.py` 100%, `utils.py` 100% 커버리지
- [x] ruff check all passed
- [x] tsc --noEmit: SPEC-STOCK-017 관련 오류 0개

---

## 결정 로그 (Decision Log)

- **온더플라이 계산** 채택 — 성과는 현재가 의존이라 스냅샷은 즉시 stale. 신규 마이그레이션 없음(최신 0015 유지).
- **가격 소스 = `get_current_price`** — Redis TTL 60초 캐시 내장. 기존 캐시 없는 자체 `_get_current_price` 대체.
- **차트 = recharts 도넛** — `recharts ^2.14.1` 이미 설치, PieChart는 신규 사용.
- **기존 엔드포인트 확장** — 신규 경로 추가 아님. `GET /portfolios/{id}/performance` 응답만 확장(하위호환).
