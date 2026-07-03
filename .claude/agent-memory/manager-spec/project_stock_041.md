---
name: project-stock-041
description: SPEC-STOCK-041 포트폴리오 목표 관리 — 목표 CRUD·달성률·달성 알림, 신규 마이그 0025(테이블 1개)
metadata:
  type: project
---

SPEC-STOCK-041 = 포트폴리오 목표 관리 (Portfolio Goal Management). status draft, version 0.1.0, branch feature/SPEC-STOCK-036.

목표(목표금액/목표수익률/기한) 설정·달성률 추적·달성 100% 시 알림. **단일 spec.md 파일**(작업지시 기준, plan/acceptance 미요청).

**Why:** SPEC-026/036으로 현재 상태는 관측 가능하나 목표 대비 진척도 추적 수단 부재가 동기.

**How to apply:** 후속 SPEC/RUN 시 아래 코드베이스 정합성 사실 준수.

핵심 사실:
- 진짜 신규 테이블 `portfolio_goals` (마이그 0025, down_revision=0024). 컬럼: id, portfolio_id FK CASCADE, target_amount Numeric(15,2) nullable, target_return_rate Numeric(8,4) nullable, deadline Date nullable, is_active Bool default True, goal_reached_notified Bool default False, created_at, updated_at. 활성목표 1개는 **앱 레벨** 강제(부분 유일제약 대신).
- REQ 접두사 REQ-GOAL-001~007. API: POST/GET(204 if none)/DELETE(soft) `/portfolios/{id}/goals`. 소유권 위반=404(403 아님).
- 달성률: 금액=(current_value/target_amount)*100, 수익률=(current_return_rate/target_return_rate)*100, 둘 다 설정 시 MIN. 0 나눗셈 가드.
- T-001~T-010 (test_portfolio_goal_041.py). AC-1~11.
- 제외(영구): 자동매매. 제외(MVP): 자동리밸런싱·포트폴리오당 다중목표·신규알림채널·목표수정PUT·달성임박사전알림·scipy·달성이력시계열.

**⚠️ 작업지시서 오류 정정 (실제 코드 확인됨):**
1. 마이그레이션 경로 = `backend/alembic/versions/` (작업지시의 `backend/src/stock_picker/migrations/versions/` 는 부재). 최신=0024.
2. `portfolio/performance.py` **존재하지 않음**. 현재 평가액/수익률 단일 진입점 = `portfolio/service.py:calculate_performance(db, portfolio_id, user_id)` (@MX:ANCHOR, 반환 dict: total_invested/total_current/total_return_pct/holdings/classification_summary/sector_performance). current_value←total_current, current_return_rate←total_return_pct.
3. `_build_portfolio_data()` 위치 = `portfolio/ai_analysis.py:76` (AI 입력용). 목표 진척도엔 calculate_performance 우선.
4. 알림 재사용(SPEC-036 portfolio_alerts.py): 이메일 `email_service.send_general_alert_email`, 텔레그램 `telegram.notifier._send_message_sync`, notifications 멱등 UNIQUE `uq_notification_user_type_code_date`(krx_code에 PORT_{id} 컨벤션), 스케줄러 `check_all_portfolio_alerts` 예외격리 패턴.
5. 스케줄러 60분 잡은 scheduler/jobs.py 등록. lifespan 기동 자체는 SPEC-022 영역(범위 밖).

연결: [[stock-picker-spec-conventions]] [[project_stock_036]]
