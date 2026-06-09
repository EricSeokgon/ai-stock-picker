# SPEC-STOCK-003 Progress

- Started: 2026-06-09
- Status: planned (구현 미착수)
- Harness: standard (3 domains, 12+ files)
- Execution Mode: TBD (run 단계에서 결정)
- Language: Python (backend) + TypeScript/React (frontend)
- Development Mode: TDD (quality.yaml 기준)

## 수용 기준 진행 현황 (전체 pending)

### Phase A — WebSocket 실시간 시세 (REQ-WS)
- [ ] REQ-WS-001 유효 종목 연결 시 즉시 최신 가격 1건 전송
- [ ] REQ-WS-002 약 10초 주기 가격 갱신 push
- [ ] REQ-WS-003 메시지에 krx_code/price/change_pct/timestamp 포함
- [ ] REQ-WS-004 연결 종료 시 폴링 루프 자원 회수
- [ ] REQ-WS-005 잘못된 krx_code 오류 후 연결 종료
- [ ] REQ-WS-006 조회 실패 주기 스킵·로그 후 재시도(연결 유지)
- [ ] REQ-WS-007 동일 종목 다중 연결 시 최신 가격 캐시 공유

### Phase B — 종목 관심 목록 (REQ-WL)
- [ ] REQ-WL-001 GET /watchlist 목록 반환
- [ ] REQ-WL-002 POST /watchlist 종목 추가
- [ ] REQ-WL-003 DELETE /watchlist/{krx_code} 종목 제거
- [ ] REQ-WL-004 (user_id, krx_code) 중복 방지
- [ ] REQ-WL-005 미인증 401
- [ ] REQ-WL-006 중복/미존재/타사용자 조작 거부(409/404/403)
- [ ] REQ-WL-007 관심 목록 페이지 실시간 시세 표시
- [ ] REQ-WL-008 추천 카드 별표 토글 추가/제거
- [ ] REQ-WL-009 미인증 별표 토글 비활성/로그인 유도

### Phase C — 포트폴리오 AI 분석 (REQ-PAI)
- [ ] REQ-PAI-001 본인 포트폴리오 Claude 분석 요청
- [ ] REQ-PAI-002 한국어 분산/리스크/개선 제안 반환
- [ ] REQ-PAI-003 입력에 식별정보 제외, 섹터/비중/수익률 포함
- [ ] REQ-PAI-004 미인증/타사용자 401·403 거부
- [ ] REQ-PAI-005 빈 포트폴리오 Claude 미호출 안내
- [ ] REQ-PAI-006 Claude 실패/타임아웃 명확한 오류 반환
- [ ] REQ-PAI-007 응답에 투자 면책 문구 포함

### 프론트엔드 (REQ-FE)
- [ ] REQ-FE-001 useLivePrice 훅
- [ ] REQ-FE-002 포트폴리오/상세 모달 실시간 시세 배지
- [ ] REQ-FE-003 관심 목록 페이지 실시간 시세 + 삭제
- [ ] REQ-FE-004 추천 카드 별표 토글 아이콘
- [ ] REQ-FE-005 포트폴리오 AI 분석 확장 섹션 + 면책
- [ ] REQ-FE-006 WebSocket 끊김 시 마지막 가격 유지·재연결

### 비기능 (REQ-NFR)
- [ ] REQ-NFR-001 운영 WSS 처리
- [ ] REQ-NFR-002 비차단 비동기 WebSocket 처리
- [ ] REQ-NFR-003 구조화 로그(토큰 원문 제외)
- [ ] REQ-NFR-004 시크릿 환경 변수 관리
- [ ] REQ-NFR-005 기존 SPEC-STOCK-001/002 하위 호환 유지

## 반복 로그 (Iteration Log)
- (run 단계에서 수용 기준 완료 수·오류 델타를 회차별로 기록)
