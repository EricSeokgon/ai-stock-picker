# SPEC-STOCK-011 구현 작업 분해 (Tasks)

상태: PLANNING
우선순위 표기: High / Medium / Low (시간 추정 없음)

---

## Milestone 1: 프론트엔드 린트 선행 작업 (REQ-CI-FE-LINT)

> 프론트엔드에 ESLint 설정·스크립트가 없으므로 CI에서 `npm run lint`를 실행하기 전에 선행 구성이 필요하다.

- **T1.1** [High] `frontend/eslint.config.js` 작성 — ESLint 9 flat config, React + TypeScript 대상. `@eslint/js` recommended + `typescript-eslint` + `eslint-plugin-react-hooks` 최소 구성.
- **T1.2** [High] `frontend/package.json` 수정 — `"lint": "eslint ."` 스크립트 추가, devDependency에 `eslint`·`typescript-eslint`·`@eslint/js`·`eslint-plugin-react-hooks` 추가, `package-lock.json` 갱신(`npm install`).
- **T1.3** [Medium] 기존 소스(`frontend/src`)에 대해 `npm run lint` 로컬 실행 후 위반 0건 확보(필요 시 규칙 완화 또는 코드 수정 — 스코프 최소화 위해 `error` 최소·`warn` 우선).

## Milestone 2: CI 워크플로 (REQ-CI-BE-*, REQ-CI-FE-*, REQ-CI-DKR-*)

- **T2.1** [High] `.github/workflows/ci.yml` 생성 — 트리거: `push`(branches: master) + `pull_request`(branches: master).
- **T2.2** [High] `backend-ci` 잡 작성:
  - `actions/checkout`
  - `astral-sh/setup-uv` (또는 `pip install uv`) + Python 3.11
  - `uv venv` + `uv pip install -r pyproject.toml --extra dev`
  - `uv run ruff check .` (REQ-CI-BE-LINT)
  - `uv run python -m compileall src` (REQ-CI-BE-TYPECHECK)
  - `uv run pytest --cov=src --cov-report=term --cov-fail-under=85` (REQ-CI-BE-TEST, REQ-CI-BE-COV)
  - working-directory: `backend`
- **T2.3** [High] `frontend-ci` 잡 작성:
  - `actions/checkout`
  - `actions/setup-node` (node 20, `cache: npm`, `cache-dependency-path: frontend/package-lock.json`)
  - `npm ci`
  - `npm run lint` (REQ-CI-FE-LINT)
  - `npm test` (REQ-CI-FE-TEST)
  - `npm run build` (REQ-CI-FE-BUILD)
  - working-directory: `frontend`
- **T2.4** [Medium] `docker-build` 잡 작성:
  - `docker/setup-buildx-action`
  - `docker/build-push-action`으로 `backend/Dockerfile` 빌드(`push: false`) (REQ-CI-DKR-BACKEND)
  - `docker/build-push-action`으로 `frontend/Dockerfile` 빌드(`push: false`) (REQ-CI-DKR-FRONTEND)
  - GitHub Actions cache(`cache-from`/`cache-to: gha`) 적용 (REQ-NFR-CACHE)
- **T2.5** [Low] 세 CI 잡을 병렬 실행되도록 구성(잡 간 `needs` 의존성 없이) (REQ-NFR-PARALLEL).

## Milestone 3: CD 워크플로 (REQ-CD-*)

- **T3.1** [High] `.github/workflows/cd.yml` 생성(또는 ci.yml 내 `cd` 잡 통합) — 트리거: `push`(branches: master)만. PR 제외 (REQ-CD-TRIGGER).
- **T3.2** [High] CD 잡에 `permissions: { contents: read, packages: write }` 설정 (REQ-CD-AUTH).
- **T3.3** [High] `docker/login-action`으로 `ghcr.io` 로그인 — username `${{ github.actor }}`, password `${{ secrets.GITHUB_TOKEN }}` (REQ-CD-AUTH, REQ-NFR-SECRET).
- **T3.4** [High] `docker/metadata-action`로 태그 생성 — `type=raw,value=latest` + `type=sha,format=long` (REQ-CD-TAG).
- **T3.5** [High] 백엔드 이미지 빌드·푸시 — `ghcr.io/${{ github.repository_owner }}/ai-stock-picker-backend` (REQ-CD-PUSH-BACKEND).
- **T3.6** [High] 프론트엔드 이미지 빌드·푸시 — `ghcr.io/${{ github.repository_owner }}/ai-stock-picker-frontend` (REQ-CD-PUSH-FRONTEND).
- **T3.7** [Medium] CD 잡이 CI 잡 성공에 의존하도록 게이트 구성 — 통합 워크플로면 `needs: [backend-ci, frontend-ci, docker-build]`, 분리 워크플로면 `workflow_run`으로 CI 성공 후 트리거 (REQ-CD-GATE).

## Milestone 4: 검증 (acceptance.md 연계)

- **T4.1** [High] PR 생성 시 CI 3개 잡이 모두 실행되고 CD가 실행되지 않음을 확인.
- **T4.2** [High] master push 시 CI 통과 후 CD가 실행되어 ghcr.io에 두 이미지가 `latest`+SHA 태그로 푸시됨을 확인.
- **T4.3** [Medium] 의도적 린트/테스트 실패 PR로 CI 게이트가 머지를 차단함을 확인.

---

## 의존성 메모

- M1(프론트 린트)은 M2의 `frontend-ci` 잡보다 먼저 완료되어야 한다(`npm run lint`가 존재해야 CI 통과).
- M3(CD)는 M2(CI) 완료 후 게이트 구성을 위해 진행한다.
- 백엔드 CI는 testcontainers 사용으로 러너 Docker 필요(`ubuntu-latest` 기본 제공).
