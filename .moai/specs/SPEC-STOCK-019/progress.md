# Progress — SPEC-STOCK-019 배당 포트폴리오 분석 (Phase 19)

- **상태**: SYNC COMPLETE
- **생성**: 2026-06-15
- **갱신**: 2026-06-15
- **작성자**: ircp

---

## 현재 단계

| 단계 | 상태 |
|------|------|
| Plan (기획) | 완료 |
| Run (구현) | 완료 |
| Sync (문서화) | 완료 |

---

## 마일스톤 진행

| 마일스톤 | 설명 | 상태 |
|----------|------|------|
| M1 | 배당 응답 스키마 추가 (`HoldingDividend`·`DividendCalendarMonth`·`PortfolioDividends`) | DONE |
| M2 | 배당 데이터 조회 (FDR 베스트에포트 + Redis 캐시 `dividends:{krx_code}` TTL 86400, REQ-DIV-002·API-004·API-005) | DONE |
| M3 | 배당 집계 서비스 (`portfolio/dividends.py`: income·가중평균 yield·캘린더·YoY) | DONE |
| M4 | 라우터 (`GET /portfolios/{id}/dividends`, 인증·소유권 404) | DONE |
| M5 | 프론트 배당 섹션 (요약 카드·캘린더·종목 테이블·N/A·로딩) | DONE |
| M6 | 테스트 & 품질 게이트 (백엔드 16개 통과·프론트 7개 통과, 총 231/205+16 통과) | DONE |
| M7 | 문서화 (README·CHANGELOG·progress 동기화) | DONE |

---

## 핵심 설계 결정 (Plan 단계)

1. **신규 DB 테이블·마이그레이션 없음** — 배당 데이터는 보유 종목 단위 실시간 조회 + Redis 캐시
   (`dividends:{krx_code}` TTL 86400s). 마이그레이션은 0016 유지.
2. **데이터 출처 = FinanceDataReader 베스트에포트** — pykrx 등 신규 공급자 미추가.
   DPS·배당수익률·배당기준일을 가능한 범위에서 조회, 없으면 N/A.
3. **`stock_fundamentals` 테이블 비의존** — SPEC-018의 `dividend_yield` 컬럼은 적재 생산자가 없어
   비어 있음(018 M2 DEFERRED). 본 SPEC은 그 테이블을 읽지 않고 독립 동작.
4. **지급월 미상 종목은 캘린더에서 제외** — 추측 단언 금지(REQ-DIV-022). 한국 일반 가정
   (12월 결산 → 연 1회·익년 4월 전후 지급)은 참고만, 단언하지 않음.
5. **기존 엔드포인트 불변** — `POST /portfolios/{id}/ai-analysis`·`GET /performance` 미수정.
   신규 `GET /portfolios/{id}/dividends`만 추가.
6. **prices.py 패턴 재사용** — `run_in_executor`로 동기 FDR 격리 + `redis.asyncio` 캐시 +
   장애 시 graceful degradation.

---

## 미해결 이슈 (Plan 단계에서 사용자 확인 필요)

- **SPEC-018 ↔ SPEC-019 명명 충돌**: SPEC-018 `progress.md`는 SPEC-STOCK-019를 "펀더멘털 일일 수집
  잡(M2)"의 구현처로 예약해 두었으나, 본 SPEC은 "배당 포트폴리오 분석"으로 배정됨. 본 SPEC은 018 M2의
  전체 KRX 수집 잡을 **포함하지 않고** 보유 종목 실시간 조회로 우회하여 충돌을 회피함. 018 M2(전체
  유니버스 수집 잡)는 여전히 미구현 상태로 남으며, 향후 별도 번호의 SPEC으로 다뤄야 함.

---

## 제외 항목 (Exclusions)

- 자동 매매·주문 (영구 제외)
- 전체 KRX 유니버스 배당/펀더멘털 일일 수집 잡 (SPEC-018 M2 영역)
- 신규 DB 테이블·마이그레이션
- 신규 데이터 공급자(pykrx 등)
- 세후/원천징수 배당 계산
- 배당 재투자(DRIP)·재투자 백테스트
- 배당 기반 추천 재가중
- 배당락 알림·인박스 연동
- `POST /portfolios/{id}/ai-analysis` 수정
