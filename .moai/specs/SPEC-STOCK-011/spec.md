---
id: SPEC-STOCK-011
version: 0.1.0
status: PLANNING
created: 2026-06-11
updated: 2026-06-11
author: ircp
priority: HIGH
issue_number: null
---

# SPEC-STOCK-011: GitHub Actions CI/CD 파이프라인

## HISTORY

- 2026-06-11 (v0.1.0): 초안 작성. Phase 12 — GitHub Actions 기반 CI(린트·타입체크·테스트·Docker 빌드 검증) + CD(ghcr.io 이미지 빌드·푸시). SPEC-STOCK-010(Docker 컨테이너화) 산출물 위에 구축.

---

## 1. 개요 (Overview)

ai-stock-picker는 SPEC-STOCK-010에서 `docker compose up` 단일 명령으로 전체 스택(db+redis+backend+frontend)을 기동할 수 있게 되었다. 그러나 코드 품질 검증과 이미지 배포는 여전히 수동이다.

본 SPEC은 **GitHub Actions 기반 CI/CD 파이프라인**을 구축한다. 이는 기능(feature)이 아니라 **운영 인프라 SPEC**이며, SPEC-STOCK-010에 이은 두 번째 인프라 SPEC이다.

목표:
- **CI**: master 브랜치로의 모든 push·PR에서 백엔드/프론트엔드 린트·테스트와 Docker 이미지 빌드를 자동 검증한다.
- **CD**: master 브랜치 push 시에만 Docker 이미지를 GitHub Container Registry(ghcr.io)에 빌드·푸시한다.

기존 자산 재사용:
- `backend/Dockerfile`(멀티스테이지·uv·Python 3.11), `frontend/Dockerfile`(node:20-alpine→nginx:alpine) — SPEC-STOCK-010 산출물을 그대로 사용.
- 백엔드 테스트 526개·프론트엔드 테스트 136개 — 전부 통과 기준.

---

## 2. 환경 및 전제 (Environment & Assumptions)

### 2.1 환경

- CI/CD 플랫폼: GitHub Actions (워크플로 파일은 `.github/workflows/`에 위치)
- 기본 브랜치: `master`
- 컨테이너 레지스트리: GitHub Container Registry (`ghcr.io`)
- 백엔드: Python 3.11, 패키지 매니저 `uv`, 테스트 `pytest`, 린트 `ruff`
- 프론트엔드: Node.js 20, 빌드 `npm run build`(`tsc && vite build`), 테스트 `npm test`(`vitest run`)

### 2.2 전제

- A1. `.github/workflows/` 디렉터리는 현재 존재하지 않는다. 본 SPEC이 신규 생성한다.
- A2. ghcr.io 푸시는 GitHub Actions 기본 제공 `GITHUB_TOKEN`(권한 `packages: write`)으로 수행하며, 별도 시크릿 발급은 불필요하다.
- A3. 백엔드 테스트는 `testcontainers[postgresql]`·`fakeredis`를 사용하므로 CI 러너에 Docker가 필요하다(GitHub-hosted `ubuntu-latest`는 Docker 제공).
- A4. **[확인 필요 사실]** 프론트엔드에는 현재 ESLint 설정 파일과 `lint` 스크립트가 **존재하지 않는다**(`package.json`에 `lint` 스크립트 없음, `.eslintrc`·`eslint.config.js` 없음). 본 SPEC은 스코프상 "Frontend: lint (eslint)"를 요구하므로, **최소 ESLint 설정(flat config)과 `lint` 스크립트 추가**를 선행 작업으로 포함한다(REQ-CI-FE-LINT 참조).

---

## 3. 요구사항 (Requirements, EARS)

### 3.1 CI — 백엔드 (REQ-CI-BE-*)

- **REQ-CI-BE-LINT** (Event-Driven)
  WHEN master 브랜치로 push 또는 PR이 발생하면, THEN the system SHALL `backend` 디렉터리에서 `ruff check`를 실행하고, 위반이 있으면 잡(job)을 실패시킨다.

- **REQ-CI-BE-TYPECHECK** (Event-Driven)
  WHEN master 브랜치로 push 또는 PR이 발생하면, THEN the system SHALL `backend`에서 `ruff check`(린트)와 별도로 타입 검증을 수행한다. 프로젝트에 별도 타입체커 의존성이 없으므로 타입 검증은 `python -m compileall src`(임포트·구문 검증) 수준으로 수행한다.

- **REQ-CI-BE-TEST** (Event-Driven)
  WHEN master 브랜치로 push 또는 PR이 발생하면, THEN the system SHALL `backend`에서 `pytest`를 실행하고, 하나라도 실패하면 잡을 실패시킨다.

- **REQ-CI-BE-COV** (State-Driven)
  WHILE `pytest`가 실행되는 동안, the system SHALL 커버리지를 측정하고 `pyproject.toml`의 `fail_under = 85` 기준 미만이면 잡을 실패시킨다.

### 3.2 CI — 프론트엔드 (REQ-CI-FE-*)

- **REQ-CI-FE-LINT** (Ubiquitous)
  The system SHALL `frontend`에 최소 ESLint flat config(`eslint.config.js`)와 `npm run lint` 스크립트를 제공하고, CI에서 `npm run lint`를 실행하여 위반 시 잡을 실패시킨다.

- **REQ-CI-FE-TEST** (Event-Driven)
  WHEN master 브랜치로 push 또는 PR이 발생하면, THEN the system SHALL `frontend`에서 `npm test`(`vitest run`)를 실행하고, 하나라도 실패하면 잡을 실패시킨다.

- **REQ-CI-FE-BUILD** (Event-Driven)
  WHEN master 브랜치로 push 또는 PR이 발생하면, THEN the system SHALL `frontend`에서 `npm run build`를 실행하여 타입체크(`tsc`)와 프로덕션 빌드를 검증한다.

### 3.3 CI — Docker 빌드 검증 (REQ-CI-DKR-*)

- **REQ-CI-DKR-BACKEND** (Event-Driven)
  WHEN master 브랜치로 push 또는 PR이 발생하면, THEN the system SHALL `backend/Dockerfile`을 빌드하여 이미지가 성공적으로 생성되는지 검증한다(푸시는 하지 않음).

- **REQ-CI-DKR-FRONTEND** (Event-Driven)
  WHEN master 브랜치로 push 또는 PR이 발생하면, THEN the system SHALL `frontend/Dockerfile`을 빌드하여 이미지가 성공적으로 생성되는지 검증한다(푸시는 하지 않음).

### 3.4 CD — 이미지 빌드·푸시 (REQ-CD-*)

- **REQ-CD-TRIGGER** (State-Driven)
  IF 이벤트가 master 브랜치로의 push이면, THEN the system SHALL CD 잡을 실행한다. PR 이벤트에서는 CD 잡을 실행하지 않는다.

- **REQ-CD-GATE** (State-Driven)
  IF CI 잡(백엔드·프론트엔드·Docker 빌드 검증)이 모두 성공하지 않았다면, THEN the system SHALL CD 잡을 실행하지 않는다.

- **REQ-CD-PUSH-BACKEND** (Event-Driven)
  WHEN CD 잡이 실행되면, THEN the system SHALL 백엔드 이미지를 빌드하여 `ghcr.io/{owner}/ai-stock-picker-backend`로 푸시한다.

- **REQ-CD-PUSH-FRONTEND** (Event-Driven)
  WHEN CD 잡이 실행되면, THEN the system SHALL 프론트엔드 이미지를 빌드하여 `ghcr.io/{owner}/ai-stock-picker-frontend`로 푸시한다.

- **REQ-CD-TAG** (Ubiquitous)
  The system SHALL 푸시되는 각 이미지에 `latest` 태그와 커밋 git SHA 태그(전체 SHA)를 동시에 부여한다.

- **REQ-CD-AUTH** (Ubiquitous)
  The system SHALL ghcr.io 인증에 GitHub Actions 기본 `GITHUB_TOKEN`(권한 `packages: write`)을 사용하고, 추가 시크릿을 요구하지 않는다.

### 3.5 비기능 요구사항 (REQ-NFR-*)

- **REQ-NFR-CACHE** (Optional)
  WHERE 가능하면, the system SHALL 의존성 캐시(uv·npm)와 Docker layer 캐시(GitHub Actions cache)를 활용하여 파이프라인 시간을 단축한다.

- **REQ-NFR-PARALLEL** (Optional)
  WHERE 가능하면, the system SHALL 백엔드·프론트엔드·Docker 빌드 CI 잡을 병렬로 실행한다.

- **REQ-NFR-SECRET** (Unwanted)
  The system SHALL NOT 시크릿·자격증명을 워크플로 파일·로그·이미지에 하드코딩한다. 모든 자격증명은 GitHub Actions 시크릿 또는 기본 `GITHUB_TOKEN`으로만 주입한다.

---

## 4. 제외 범위 (Exclusions / What NOT to Build)

본 SPEC은 다음을 **명시적으로 제외**한다:

- **EXCL-1**: Kubernetes·클라우드(ECS/Cloud Run 등) 배포 — 인프라 미결정.
- **EXCL-2**: 스테이징/프로덕션 환경 실제 배포(running deployment) — 인프라 미준비. CD는 이미지 빌드·푸시까지만.
- **EXCL-3**: GitHub Actions 시크릿을 넘어선 시크릿 관리(Vault·클라우드 시크릿 매니저).
- **EXCL-4**: TLS 인증서 발급, 도메인 연결, 리버스 프록시 운영 구성.
- **EXCL-5**: 모니터링/관측(Prometheus·Grafana·Sentry) 통합.
- **EXCL-6**: 자동 매매·주문 실행 — 규제·책임 리스크로 **영구 제외**(프로젝트 전역 규약).
- **EXCL-7**: 백엔드 타입체커(mypy/pyright) 신규 도입 — 현재 의존성에 없으며, 타입 검증은 `compileall` 수준으로 한정.
- **EXCL-8**: 릴리스 태깅(semver), 체인지로그 자동화, GitHub Release 생성.

---

## 5. 산출물 (Deliverables)

신규 파일:
- `.github/workflows/ci.yml` — CI 워크플로(백엔드·프론트엔드·Docker 빌드 검증, push/PR 트리거).
- `.github/workflows/cd.yml` — CD 워크플로(ghcr.io 빌드·푸시, master push 트리거). 또는 `ci.yml` 내 CD 잡으로 통합 가능(plan/tasks에서 결정).
- `frontend/eslint.config.js` — 최소 ESLint flat config(REQ-CI-FE-LINT).

수정 파일:
- `frontend/package.json` — `lint` 스크립트 추가, `eslint`·관련 플러그인 devDependency 추가.

---

## 6. 관련 SPEC

- SPEC-STOCK-010 (Docker 컨테이너화): 본 SPEC이 빌드·푸시하는 Dockerfile의 출처. 재정의하지 않고 그대로 사용.
