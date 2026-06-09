# SPEC-STOCK-004 Progress

- Started: 2026-06-09
- Status: planned (구현 미착수)
- Harness: standard (2 domains, 10+ files)
- Execution Mode: TBD (run 단계에서 결정)
- Language: Python (backend) + TypeScript/React (frontend)
- Development Mode: TDD (quality.yaml 기준)

## 수용 기준 진행 현황 (전체 pending)

### Phase A — 관심 목록 가격 알림 (REQ-WALERT)
- [ ] REQ-WALERT-001 POST /watchlist/alerts 목표가 알림 생성(is_active=true)
- [ ] REQ-WALERT-002 GET /watchlist/alerts 알림 목록 반환
- [ ] REQ-WALERT-003 DELETE /watchlist/alerts/{id} 알림 삭제
- [ ] REQ-WALERT-004 5분 주기 활성 알림 above/below 조건 평가
- [ ] REQ-WALERT-005 조건 충족 시 텔레그램 1회 전송 + is_active=false + triggered_at 기록
- [ ] REQ-WALERT-006 텔레그램 메시지 한국어(종목명/목표가/방향/현재가)
- [ ] REQ-WALERT-007 미인증 401, 데이터 미노출
- [ ] REQ-WALERT-008 타사용자/미존재 알림 조작 거부(403/404)
- [ ] REQ-WALERT-009 개별 시세 조회 실패 격리(스킵·로그·재평가)
- [ ] REQ-WALERT-010 텔레그램 미구독 시 안전 스킵(triggered 기록 유지)

### Phase B — 이메일 알림 (REQ-EMAIL)
- [ ] REQ-EMAIL-001 POST /notifications/email 구독(저장/재활성화)
- [ ] REQ-EMAIL-002 DELETE /notifications/email 구독 해지(is_active=false)
- [ ] REQ-EMAIL-003 smtplib+email 사용, SMTP 접속정보 환경 변수
- [ ] REQ-EMAIL-004 가격 도달 시 활성 구독자에 메일 발송
- [ ] REQ-EMAIL-005 월요일 07:00 KST 주간 추천 요약(상위 5개) 발송
- [ ] REQ-EMAIL-006 메일 본문 면책·해지 안내 포함
- [ ] REQ-EMAIL-007 SMTP 실패 시 수신자 단위 격리(다른 발송 계속)
- [ ] REQ-EMAIL-008 유효하지 않은 이메일 422 거부
- [ ] REQ-EMAIL-009 미인증 401, 구독 미변경

### 프론트엔드 (REQ-FE)
- [ ] REQ-FE-001 Watchlist 종목별 목표가 알림 추가 UI(목표가+이상/이하)
- [ ] REQ-FE-002 활성 가격 알림 목록·삭제 표시
- [ ] REQ-FE-003 /settings 이메일 구독 토글·상태 페이지
- [ ] REQ-FE-004 /settings 라우트 등록 + 인증 가드
- [ ] REQ-FE-005 알림/구독 요청 실패 시 오류 표시·UI 롤백

### 비기능 (REQ-NFR)
- [ ] REQ-NFR-001 구조화 로그(자격 증명 원문 제외)
- [ ] REQ-NFR-002 시크릿 환경 변수 관리
- [ ] REQ-NFR-003 가격 점검 알림 단위 예외 격리
- [ ] REQ-NFR-004 기존 SPEC-STOCK-001/002/003 하위 호환 유지
- [ ] REQ-NFR-005 기존 스케줄러에 신규 작업만 추가(기존 트리거 불변)

## 반복 로그 (Iteration Log)
- (run 단계에서 수용 기준 완료 수·오류 델타를 회차별로 기록)
