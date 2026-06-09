---
name: stock-picker-spec-conventions
description: SPEC conventions for the ai-stock-picker (Korean Stock & ETF Recommendation System) project
metadata:
  type: project
---

ai-stock-picker 프로젝트(한국 주식 & ETF 추천 시스템)의 SPEC 작성 규약.

**Facts:**
- SPEC ID 체계: `SPEC-STOCK-NNN` (001 = MVP/Phase 1·2, 002 = Phase 3 인증·텔레그램·포트폴리오·백테스팅, 003 = Phase 4 WebSocket 실시간 시세·관심목록·포트폴리오 AI 분석).
- spec/plan/acceptance 본문은 **한국어**로 작성. EARS 키워드(WHEN/WHILE/WHERE/IF...THEN/SHALL)와 코드·식별자만 영어.
- spec.md frontmatter 8필드: id, version, status, created, updated, author(=ircp), priority, issue_number.
- REQ 네이밍은 기능 도메인별 접두사 사용: REQ-NEWS-*, REQ-AI-*, REQ-AUTH-*, REQ-TG-*, REQ-PORT-*, REQ-BT-*, REQ-WS-*, REQ-WL-*, REQ-PAI-*, REQ-FE-*, REQ-NFR-*.
- 002까지는 spec/plan/acceptance 3파일 구조였으나, 003은 spec/tasks/progress 3파일로 작성됨(사용자 요청 형식). DB 마이그레이션은 누적: 001~005 존재, 003의 신규 테이블 watchlist_items = 0006.
- 기술 스택은 확정·재사용: FastAPI + PostgreSQL + Redis + React + Recharts + FinanceDataReader + APScheduler + Claude API. 신규 SPEC은 기존 테이블·API를 재정의하지 말고 추가만 할 것.

**Why:** 사용자가 단일 일관된 SPEC 스타일과 한국어 본문을 명시적으로 요구함. Phase별로 SPEC을 나누되 번호는 연속.

**How to apply:** 이 프로젝트의 새 SPEC 작성 시 위 ID 체계·한국어 본문·REQ 접두사·frontmatter 형식을 따르고, SPEC-STOCK-001의 자산은 재사용 대상으로 명시.

**영구 제외 (절대 SPEC에 포함 금지):** 자동 매매/주문 실행 — 규제·책임 리스크로 영구 제외. (이메일 알림·소셜 로그인은 Phase 4 연기이지 영구 제외 아님.)
