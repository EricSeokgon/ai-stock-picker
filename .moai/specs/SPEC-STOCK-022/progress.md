# SPEC-STOCK-022 진행 상황

대상: Docker 컨테이너화 커밋 및 운영 환경 검증 (Phase 22)
상태: DONE (PLAN 완료, RUN 완료, SYNC 완료)

---

## 현재 상태

- [x] PLAN: 리서치 및 SPEC 작성 완료 (2026-06-15)
- [x] RUN: 구현 완료 (스케줄러 lifespan 연동 + 검증) (2026-06-15)
  - commit ef88160: APScheduler lifespan 통합
  - `setup_scheduler()` 호출 + scheduler.start/shutdown
  - `ENABLE_SCHEDULER` 환경변수 토글 (default true)
  - test_lifespan_scheduler.py 4개 테스트 전부 통과
- [x] SYNC: 문서 동기화 (2026-06-15)
  - progress.md: 모든 체크박스 완료 표기
  - CHANGELOG.md: v0.22.0 엔트리 추가
  - README.md: 환경변수 섹션 업데이트

---

## PLAN 단계 요약

### 리서치 핵심 발견
1. **작업 전제 정정**: SPEC-010 Docker 산출물 8개는 이미 커밋됨(commit `b83b054`). "커밋" 작업 불필요 → 스코프를 "검증 + 결함 수정"으로 재정의.
2. **운영 결함 발견**: `setup_scheduler()`가 앱 기동 경로에서 호출되지 않음. 컨테이너에서 모든 배치/주기 잡(일일·장중·가격알림·주간요약·일반알림)이 실행되지 않는 상태. → SPEC-022의 핵심 가치.
3. 마이그레이션 최신 = `0017_alerts`, entrypoint가 head까지 적용. 정상.
4. 필수 env 5종 모두 `.env.example`에 존재. 선택 env 2종(`REALTIME_*`) 문서 누락.

### 산출물
- `spec.md` — REQ-022-COMMIT/SCHED/MIG/ENV/VERIFY/NFR, AC-1~13, M1~M5
- `research.md` — git 추적 상태, env 매트릭스, 스케줄러 결함 상세, Dockerfile/compose 검증
- `progress.md` — 본 파일

---

## RUN 단계 체크포인트 (예정)

- M1: 상태 검증 (git 추적 확인)
- M2: 스케줄러 lifespan 연동 (`api/main.py`) + `ENABLE_SCHEDULER` 토글 + 테스트 — **핵심**
- M3: `.env.example` 보강 + `.gitignore` 시크릿 위생
- M4: `docker compose up` 전체 스택 검증 (/health, /api 프록시, 스케줄러 로그)
- M5: 품질 게이트 (pytest 85%, ruff)

## 주의사항 (RUN 담당자용)

- 스케줄러를 lifespan에서 시작 시 **단일 backend 인스턴스 가정**. 다중 워커 시 잡 중복 발생하므로 `ENABLE_SCHEDULER` 토글 필수.
- 기존 `price_broadcast_loop` 시작 로직과 공존해야 함(둘 다 시작, 예외 격리).
- `check_price_alerts`·`_run_general_alert_check`는 DB 세션을 사용하므로 컨테이너에 `DATABASE_URL` 필수(이미 충족).
- 루트 `.env`가 이미 git에 추적 중이면 `git rm --cached .env`는 사용자 확인 후 수행(파일 자체는 삭제 금지).
