# SPEC-STOCK-011 진행 상황 (Progress)

- **SPEC ID**: SPEC-STOCK-011
- **제목**: GitHub Actions CI/CD 파이프라인 (Phase 12)
- **버전**: 1.0.0
- **상태**: DONE
- **작성자**: ircp
- **생성일**: 2026-06-11
- **갱신일**: 2026-06-11

---

## 현재 단계

| 단계 | 상태 |
|------|------|
| Plan (기획) | 완료 — spec/tasks/acceptance 작성 완료 |
| Run (구현) | 완료 |
| Sync (문서화) | 완료 |

---

## 마일스톤 진행

| 마일스톤 | 설명 | 상태 |
|----------|------|------|
| M1 | 프론트엔드 ESLint 선행 구성 | 완료 |
| M2 | CI 워크플로 (백엔드·프론트엔드·Docker 빌드) | 완료 |
| M3 | CD 워크플로 (ghcr.io 빌드·푸시) | 완료 |
| M4 | 검증 (AC-1~9) | 완료 (구조 검증) |

---

## 구현 산출물

### M1 — 프론트엔드 ESLint 선행 구성 (REQ-CI-FE-LINT)

- `frontend/eslint.config.js` 생성: ESLint 9 flat config, `@eslint/js` recommended + `typescript-eslint` + `eslint-plugin-react-hooks`
- `frontend/package.json` 수정:
  - `"lint": "eslint src"` 스크립트 추가
  - devDependencies에 `eslint@^9`, `@eslint/js@^9`, `typescript-eslint@^8`, `eslint-plugin-react-hooks@^5` 추가

### M2 — CI 워크플로 (`.github/workflows/ci.yml`)

트리거: `push` + `pull_request` → branches: master

병렬 잡 3개:

1. **backend-ci** (REQ-CI-BE-LINT, REQ-CI-BE-TYPECHECK, REQ-CI-BE-TEST, REQ-CI-BE-COV)
   - `astral-sh/setup-uv@v4` + Python 3.11
   - `uv sync --extra dev`
   - `uv run ruff check src/`
   - `uv run python -m compileall src/`
   - `uv run pytest tests/ -q --no-header --tb=short --cov=src --cov-report=term --cov-fail-under=85`
   - uv 캐시: `~/.cache/uv` (pyproject.toml 해시 키)

2. **frontend-ci** (REQ-CI-FE-LINT, REQ-CI-FE-TEST, REQ-CI-FE-BUILD)
   - `actions/setup-node@v4` (node 20, npm 캐시)
   - `npm ci`
   - `npm run lint`
   - `npm test -- --run`
   - `npm run build`

3. **docker-build** (REQ-CI-DKR-BACKEND, REQ-CI-DKR-FRONTEND)
   - `docker/setup-buildx-action@v3`
   - backend + frontend Dockerfile 빌드 (`push: false`)
   - GitHub Actions cache (`type=gha`) 적용 (REQ-NFR-CACHE)

### M3 — CD 워크플로 (`.github/workflows/cd.yml`)

트리거: `workflow_run` → CI 워크플로 완료 + master 브랜치 (REQ-CD-TRIGGER, REQ-CD-GATE)

- `if: github.event.workflow_run.conclusion == 'success'` 조건으로 CI 성공 시에만 실행
- `permissions: { contents: read, packages: write }` (REQ-CD-AUTH)
- `docker/login-action@v3` ghcr.io 로그인 — `secrets.GITHUB_TOKEN` 사용 (REQ-NFR-SECRET)
- `docker/metadata-action@v5`: `latest` + `sha:long` 태그 (REQ-CD-TAG)
- backend: `ghcr.io/${{ github.repository_owner }}/ai-stock-picker-backend` (REQ-CD-PUSH-BACKEND)
- frontend: `ghcr.io/${{ github.repository_owner }}/ai-stock-picker-frontend` (REQ-CD-PUSH-FRONTEND)

---

## 결정·이슈 로그

- 2026-06-11: SPEC 초안 작성. SPEC-STOCK-010 Docker 산출물 위에 구축하는 두 번째 인프라 SPEC.
- 2026-06-11: **이슈** — 프론트엔드에 ESLint 설정·`lint` 스크립트가 부재함을 확인. 스코프의 "Frontend: lint (eslint)" 요구를 충족하기 위해 ESLint 최소 구성 추가를 M1 선행 작업으로 포함(REQ-CI-FE-LINT).
- 2026-06-11: 백엔드 타입체크는 별도 타입체커 의존성(mypy/pyright) 부재로 `python -m compileall src` 수준으로 한정(EXCL-7).
- 2026-06-11: CD 인증은 GitHub 기본 `GITHUB_TOKEN`(`packages: write`)만 사용, 별도 시크릿 발급 없음(REQ-CD-AUTH).
- 2026-06-11: **구현 완료** — CD 게이트를 `needs` 대신 `workflow_run`으로 구현. 이유: `needs`는 같은 워크플로 내 잡 간 의존성에 사용되며, CD를 별도 워크플로 파일로 분리한 경우 CI 성공 여부를 감지하려면 `workflow_run` 이벤트가 올바른 접근. PR 이벤트 시 CI 워크플로는 실행되지만 `workflow_run.branches: [master]` 필터로 PR 브랜치 CI는 CD를 트리거하지 않음.
