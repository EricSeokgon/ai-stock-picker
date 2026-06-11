---
name: project-stock012-backtest
description: SPEC-STOCK-012 백테스트 엔진 완성 — M1~M4 + M6(BE) 구현 완료. 계약 정합, 벤치마크, 신규 지표.
metadata:
  type: project
---

SPEC-STOCK-012 (Phase 13) M1~M4 + M6(BE) 구현 완료. 커밋: 6622f15.

**Why:** 프론트엔드(`api/backtest.ts`)와 백엔드 응답 형태가 6군데 불일치 상태였음 — status enum, POST 응답 구조, 결과 시계열 형태 모두 드리프트. 핵심은 신규 기능보다 계약 정합화.

**How to apply:** 향후 백테스트 관련 변경 시 참조.

## 변경 파일 (10개)

- `backend/alembic/versions/0013_backtest_params.py` — universe_size·top_n 컬럼 추가 (신규)
- `backend/src/stock_picker/db/models.py` — BacktestRun 모델 컬럼 추가, status 코멘트 갱신
- `backend/src/stock_picker/backtest/schemas.py` — BacktestStartResponse 추가, DailyResultTimeSeries 추가, 기존 스키마 필드 확장
- `backend/src/stock_picker/backtest/metrics.py` — calculate_total_return·calculate_win_rate·build_portfolio_value_series 추가
- `backend/src/stock_picker/backtest/runner.py` — 벤치마크(KS11) 수집, _TOP_N 하드코딩 제거, universe_size/top_n 파라미터화, status "error"→"failed"
- `backend/src/stock_picker/backtest/router.py` — POST 202+{run_id,message}, GET results → flat DailyResultTimeSeries 배열
- `backend/tests/unit/test_backtest_metrics.py` — 신규 메트릭 함수 테스트 추가
- `backend/tests/unit/test_backtest_runner.py` — runner 상태전환·벤치마크실패·universe 파라미터 테스트 (신규)
- `backend/tests/integration/test_backtest_router.py` — POST 202 구조, universe/top_n 검증, flat array 결과 테스트 갱신
- `.moai/specs/SPEC-STOCK-012/progress.md` — 진행 상황 갱신

## API 계약 변경 요약

- `POST /backtest/run` → HTTP 202, 응답: `{run_id: int, message: str}`
- `GET /backtest/runs/{run_id}` → `BacktestRunDetail`에 `total_return`, `win_rate` 추가
- `GET /backtest/runs/{run_id}/results` → 페이지네이션 제거, flat `list[DailyResultTimeSeries]` 반환

## 테스트 결과

전체 551/556 통과. 5개 실패는 `test_collectors.py` HTTP mock 테스트 (이번 구현 무관, 기존 사전 존재).

## 주요 구현 패턴

- `DetachedInstanceError` 회피: DB 세션 닫기 전에 ORM 속성 모두 접근하거나, 테스트에서 직접 DB 조작 패턴 피함
- 벤치마크 실패 격리: `_fetch_benchmark_data`가 `except Exception`으로 None 반환, runner가 계속 진행
- asyncio `create_task` + `run_in_executor`: FDR 동기 호출을 이벤트 루프 블로킹 없이 실행
