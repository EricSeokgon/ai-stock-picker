# SPEC-STOCK-011 진행 상황 (Progress)

- **SPEC ID**: SPEC-STOCK-011
- **제목**: GitHub Actions CI/CD 파이프라인 (Phase 12)
- **버전**: 0.1.0
- **상태**: PLANNING
- **작성자**: ircp
- **생성일**: 2026-06-11
- **갱신일**: 2026-06-11

---

## 현재 단계

| 단계 | 상태 |
|------|------|
| Plan (기획) | 진행 중 — spec/tasks/acceptance 작성 완료 |
| Run (구현) | 대기 |
| Sync (문서화) | 대기 |

---

## 마일스톤 진행

| 마일스톤 | 설명 | 상태 |
|----------|------|------|
| M1 | 프론트엔드 ESLint 선행 구성 | 대기 |
| M2 | CI 워크플로 (백엔드·프론트엔드·Docker 빌드) | 대기 |
| M3 | CD 워크플로 (ghcr.io 빌드·푸시) | 대기 |
| M4 | 검증 (AC-1~9) | 대기 |

---

## 결정·이슈 로그

- 2026-06-11: SPEC 초안 작성. SPEC-STOCK-010 Docker 산출물 위에 구축하는 두 번째 인프라 SPEC.
- 2026-06-11: **이슈** — 프론트엔드에 ESLint 설정·`lint` 스크립트가 부재함을 확인. 스코프의 "Frontend: lint (eslint)" 요구를 충족하기 위해 ESLint 최소 구성 추가를 M1 선행 작업으로 포함(REQ-CI-FE-LINT).
- 2026-06-11: 백엔드 타입체크는 별도 타입체커 의존성(mypy/pyright) 부재로 `python -m compileall src` 수준으로 한정(EXCL-7).
- 2026-06-11: CD 인증은 GitHub 기본 `GITHUB_TOKEN`(`packages: write`)만 사용, 별도 시크릿 발급 없음(REQ-CD-AUTH).

---

## 다음 작업

- `/moai run SPEC-STOCK-011` 로 구현 단계 진입.
- 구현 시 M1(프론트 린트) → M2(CI) → M3(CD) 순으로 진행.
