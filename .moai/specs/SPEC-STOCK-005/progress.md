# SPEC-STOCK-005 Progress

- Started: 2026-06-09
- Status: planned (구현 미착수)
- Harness: standard (2 domains — backend/frontend, 10+ files)
- Execution Mode: TBD (run 단계에서 결정)
- Language: Python (backend) + TypeScript/React (frontend)
- Development Mode: TDD (quality.yaml 기준)

## 수용 기준 진행 현황 (전체 pending)

### Phase A — Redis 캐싱 레이어 (REQ-CACHE)
- [ ] REQ-CACHE-001 추천 조회 시 파라미터 대응 캐시 키 조회·히트 시 즉시 반환
- [ ] REQ-CACHE-002 캐시 미스 시 기준 추천 가공·적재(TTL 1800s)·반환
- [ ] REQ-CACHE-003 캐시 키 패턴 준수(recommendations:{date} 불변, top:{limit}, sector:{sector})
- [ ] REQ-CACHE-004 기준 추천 갱신 시 파생 키 무효화
- [ ] REQ-CACHE-005 현재가 price:{krx_code} TTL 60s 캐시·미스 시 FDR 적재
- [ ] REQ-CACHE-006 REDIS_URL 환경 변수(기본 redis://localhost:6379/0)
- [ ] REQ-CACHE-007 [HARD] Redis 미가용/실패 시 폴백·기능 무중단
- [ ] REQ-CACHE-008 손상 캐시 역직렬화 실패 시 미스 처리

### Phase B — 추천 필터 & 정렬 (REQ-FILTER)
- [ ] REQ-FILTER-001 ?limit 상위 N개 반환
- [ ] REQ-FILTER-002 ?sector 섹터 필터
- [ ] REQ-FILTER-003 ?sort score/sentiment/volume 내림차순(기본 score)
- [ ] REQ-FILTER-004 ?min_score 최소 점수 필터
- [ ] REQ-FILTER-005 파라미터 조합·기본 호출 하위 호환
- [ ] REQ-FILTER-006 잘못된 파라미터 422/기본값(500 금지)
- [ ] REQ-FILTER-007 빈 결과 정상 응답([])

### 프론트엔드 필터 바 (REQ-FE)
- [ ] REQ-FE-001 필터 바(섹터 드롭다운·정렬·최소 점수)
- [ ] REQ-FE-002 섹터 드롭다운 동적 구성
- [ ] REQ-FE-003 필터 변경 시 쿼리 파라미터 반영·재조회
- [ ] REQ-FE-004 필터 초기화 버튼
- [ ] REQ-FE-005 조회 실패 시 오류 표시·직전 상태 유지

### Phase C — 모바일 반응형 (REQ-RESP)
- [ ] REQ-RESP-001 <768px 네비게이션 햄버거 메뉴
- [ ] REQ-RESP-002 <768px 추천 목록 세로 카드 레이아웃
- [ ] REQ-RESP-003 <768px 포트폴리오 표 반응형(스크롤/카드)
- [ ] REQ-RESP-004 <768px 관심 목록 컴팩트 카드
- [ ] REQ-RESP-005 CSS 미디어 쿼리만 사용(신규 의존성 0)
- [ ] REQ-RESP-006 >=768px 데스크톱 레이아웃·동작 불변

### 비기능 (REQ-NFR)
- [ ] REQ-NFR-001 캐시 히트/미스·무효화·폴백 구조화 로그(시크릿 제외)
- [ ] REQ-NFR-002 [HARD] Redis 가용성과 무관하게 모든 기존 기능 동작
- [ ] REQ-NFR-003 SPEC-STOCK-001/002/003/004 하위 호환(신규 테이블·마이그레이션 없음)
- [ ] REQ-NFR-004 기존 recommendations:{date} 키·적재 주체 불변
- [ ] REQ-NFR-005 현재가 Redis 캐시 동기 호출 호환(비동기 전환 없음)

## 반복 로그 (Iteration Log)
- (run 단계에서 수용 기준 완료 수·오류 델타를 회차별로 기록)
