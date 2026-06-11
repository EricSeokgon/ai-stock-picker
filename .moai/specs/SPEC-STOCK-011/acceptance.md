# SPEC-STOCK-011 인수 기준 (Acceptance Criteria)

형식: Given-When-Then. 모든 시나리오는 관측 가능한 증거(GitHub Actions 실행 결과, 레지스트리 이미지)로 검증한다.

---

## AC-1: PR에서 CI 백엔드 잡 통과 (REQ-CI-BE-LINT, REQ-CI-BE-TEST, REQ-CI-BE-COV)

- **Given** master를 대상으로 한 PR이 열려 있고 백엔드 코드가 린트·테스트를 통과하는 상태
- **When** GitHub Actions CI 워크플로가 실행되면
- **Then** `backend-ci` 잡이 `ruff check`·`pytest`를 실행하고 커버리지 85% 이상으로 성공(녹색)한다.

## AC-2: PR에서 CI 프론트엔드 잡 통과 (REQ-CI-FE-LINT, REQ-CI-FE-TEST, REQ-CI-FE-BUILD)

- **Given** master를 대상으로 한 PR이 열려 있는 상태
- **When** CI 워크플로가 실행되면
- **Then** `frontend-ci` 잡이 `npm run lint`·`npm test`(136개 통과)·`npm run build`를 모두 성공한다.

## AC-3: PR에서 Docker 빌드 검증 통과 (REQ-CI-DKR-BACKEND, REQ-CI-DKR-FRONTEND)

- **Given** master를 대상으로 한 PR
- **When** CI 워크플로가 실행되면
- **Then** `docker-build` 잡이 `backend/Dockerfile`·`frontend/Dockerfile`을 모두 성공적으로 빌드하고, 이미지를 **푸시하지 않는다**.

## AC-4: PR에서는 CD가 실행되지 않음 (REQ-CD-TRIGGER)

- **Given** master를 대상으로 한 PR(아직 머지 전)
- **When** CI 워크플로가 실행되면
- **Then** CD(이미지 푸시) 잡은 실행되지 않는다.

## AC-5: master push 시 CD가 이미지를 푸시함 (REQ-CD-PUSH-BACKEND, REQ-CD-PUSH-FRONTEND, REQ-CD-GATE)

- **Given** CI가 모두 통과한 master 브랜치로의 push
- **When** CD 워크플로가 실행되면
- **Then** `ghcr.io/{owner}/ai-stock-picker-backend`와 `ghcr.io/{owner}/ai-stock-picker-frontend` 두 이미지가 ghcr.io 패키지 목록에 나타난다.

## AC-6: 이미지 태그 부여 (REQ-CD-TAG)

- **Given** master push로 CD가 실행된 직후
- **When** ghcr.io의 각 이미지 태그 목록을 조회하면
- **Then** 각 이미지에 `latest` 태그와 해당 커밋의 git SHA 태그가 동시에 존재한다.

## AC-7: 인증은 GITHUB_TOKEN만 사용 (REQ-CD-AUTH, REQ-NFR-SECRET)

- **Given** CD 워크플로 정의
- **When** 워크플로 YAML을 검토하면
- **Then** ghcr.io 로그인이 `secrets.GITHUB_TOKEN`만 사용하고, 별도 PAT·하드코딩 자격증명이 없으며, 잡에 `packages: write` 권한이 명시되어 있다.

## AC-8: CI 실패가 머지 게이트로 동작 (REQ-CI-BE-*, REQ-CI-FE-*)

- **Given** 백엔드 또는 프론트엔드에 의도적 린트/테스트 실패를 포함한 PR
- **When** CI 워크플로가 실행되면
- **Then** 해당 잡이 실패(적색)하고, master push로 진행되더라도 CD 잡이 실행되지 않는다(REQ-CD-GATE).

## AC-9: 프론트엔드 린트 인프라 존재 (REQ-CI-FE-LINT)

- **Given** SPEC 구현 완료 후 `frontend/` 디렉터리
- **When** `frontend/eslint.config.js` 존재 여부와 `npm run lint` 실행을 확인하면
- **Then** 설정 파일이 존재하고 `npm run lint`가 위반 0건으로 성공 종료한다.

---

## Definition of Done

- [ ] `.github/workflows/ci.yml` 존재, push·PR(master) 트리거.
- [ ] `.github/workflows/cd.yml`(또는 통합 cd 잡) 존재, master push 전용 트리거.
- [ ] `frontend/eslint.config.js` + `npm run lint` 스크립트 추가.
- [ ] AC-1 ~ AC-9 전부 충족(실제 GitHub Actions 실행 결과로 증명).
- [ ] 워크플로·이미지에 시크릿 하드코딩 0건.
- [ ] 제외 범위(EXCL-1~8) 항목이 SPEC에 포함되지 않았음을 확인.
