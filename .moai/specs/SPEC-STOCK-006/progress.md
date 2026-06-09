# SPEC-STOCK-006 Progress

- Started: 2026-06-10
- Status: planned (구현 미착수)
- Harness: standard (2 domains — backend/frontend, 10+ files)
- Execution Mode: TBD (run 단계에서 결정)
- Language: Python (backend) + TypeScript/React (frontend)
- Development Mode: TDD (quality.yaml 기준)

## 수용 기준 진행 현황 (전체 pending)

### Phase A — 추천 근거 설명 (REQ-EXPL)
- [ ] AC-A1 (REQ-EXPL-001) explanation 컬럼 추가(reasoning 보존)
- [ ] AC-A2 (REQ-EXPL-002/004) Claude 한국어 2~3문장 근거 생성·저장
- [ ] AC-A3 (REQ-EXPL-003) 추천 API 응답에 explanation 노출
- [ ] AC-A4 [HARD] (REQ-EXPL-005) Claude 실패 시 폴백·파이프라인 무중단
- [ ] AC-A5 (REQ-EXPL-006) 매수/매도·수익 보장 표현 금지

### Phase B — 추천 히스토리 조회 (REQ-HIST)
- [ ] AC-B1 (REQ-HIST-001/002) 최근 N일 날짜별 그룹화·최신 우선
- [ ] AC-B2 (REQ-HIST-001) days 기본값 7일
- [ ] AC-B3 (REQ-HIST-003) 잘못된 days 422/보정(500 금지)
- [ ] AC-B4 (REQ-HIST-004) 빈 기간 history:[] 정상 응답
- [ ] AC-B5 (REQ-HIST-005/FE-002/FE-003) 프론트 히스토리 페이지·기간 변경

### Phase C — 뉴스 감성 상세화 (REQ-SENT)
- [ ] AC-C1 (REQ-SENT-001) sentiment_label 컬럼 추가(기존 보존)
- [ ] AC-C2 (REQ-SENT-002) 5단계 매핑·저장(매우긍정~매우부정)
- [ ] AC-C3 (REQ-SENT-003) GET /news에 sentiment_label 노출
- [ ] AC-C4 (REQ-SENT-004/005) sentiment 보존·null 처리
- [ ] AC-C5 (REQ-FE-004) 프론트 5단계 감성 배지

### 횡단 — 하위 호환·안전 (REQ-NFR/REQ-SAFE)
- [ ] AC-X1 [HARD] (REQ-NFR-002/004) 신규 필드 미사용 클라이언트 하위 호환
- [ ] AC-X2 (REQ-NFR-001) 구조화 로그(시크릿 제외)
- [ ] AC-X3 [HARD] (REQ-SAFE-001/002) 면책 유지·자동 매매 영구 제외

## 설계 확정값 (요약)
- 마이그레이션 0009: recommendations.explanation(Text), analysis_results.sentiment_label(String(20)) — 둘 다 nullable
- explanation(Claude) ↔ reasoning(규칙) 분리·보존
- 히스토리: DB 직접 조회, days 기본 7·보정 1~90, trade_date 그룹화
- 감성 매핑(잠정): >=0.6 매우긍정 / >=0.2 긍정 / >-0.2 중립 / >-0.6 부정 / <=-0.6 매우부정
- 신규 응답 필드 Optional, 자동 매매 영구 제외, 면책 고지 유지

## 반복 로그 (Iteration Log)
- (run 단계에서 수용 기준 완료 수·오류 델타를 회차별로 기록)
