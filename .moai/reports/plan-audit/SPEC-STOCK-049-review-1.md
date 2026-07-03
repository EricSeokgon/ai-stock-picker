# Plan-Audit — SPEC-STOCK-049 (거래 내역 & 실현손익) — review-1

- Date: 2026-07-01
- Auditor: manager-spec (self-audit)
- Verdict: PASS

## Scope

포트폴리오 거래 원장(transaction ledger) + 이동평균 원가법 실현손익. 신규 도메인, 신규 테이블 1개(마이그레이션 0030, down_revision 0029).

## Checklist

| # | Check | Result | Note |
|---|-------|--------|------|
| C1 | 디렉터리 구조 `.moai/specs/SPEC-STOCK-049/spec.md` | PASS | flat 파일 아님 |
| C2 | ID 유일성 (049 미사용) | PASS | 048 까지 존재, 049 신규 |
| C3 | Frontmatter 8필드 (id/version/status/created/updated/author/priority/issue_number) | PASS | + branch·labels |
| C4 | EARS 준수 — 모든 REQ WHEN/IF/WHERE + SHALL | PASS | 16 REQ 전수 확인 |
| C5 | AC 단일 SHALL | PASS(주의) | AC-012 는 프론트 복합(render+display) — 048 AC-012 선례와 동일, 단일 shall 키워드 |
| C6 | Exclusions(§2.2 Out-of-Scope) ≥1 | PASS | 11개 제외 항목 |
| C7 | 자동매매 영구 제외 명시 | PASS | §2.2 첫 항목 |
| C8 | REQ→AC 추적성 | PASS | 16/16 매핑 (아래 매트릭스) |
| C9 | AC→Test 추적성 | PASS | 12/12 매핑 |
| C10 | 마이그레이션 번호 정확 | PASS | 0030, down_revision 0029 (0029 가 현재 최신 확인) |
| C11 | sync/async 규약 | PASS | 거래 서비스 sync `Session` — 홀딩스 CRUD 패턴 준수 |
| C12 | 신규 외부 의존성 0 / scipy 미사용 | PASS | Decimal + 표준 산술만 |

## REQ → AC → Test 추적 매트릭스

| REQ | AC | Test |
|-----|----|----|
| REQ-TXN-001 | AC-049-001 | T-049-001 |
| REQ-TXN-002 | AC-049-002 | T-049-002 |
| REQ-TXN-003 | AC-049-003 | T-049-003 |
| REQ-TXN-004 | AC-049-004 | T-049-004 |
| REQ-TXN-005 | AC-049-005 | T-049-005 |
| REQ-TXN-006 | AC-049-006 | T-049-006 |
| REQ-TXN-007 | AC-049-007 | T-049-007 |
| REQ-TXN-008 | AC-049-008 | T-049-008 |
| REQ-TXN-009 | AC-049-009 | T-049-009 |
| REQ-TXN-010 | AC-049-009 | T-049-009 |
| REQ-TXN-011 | AC-049-009 | T-049-009 |
| REQ-TXN-012 | AC-049-010 | T-049-010 |
| REQ-TXN-013 | AC-049-011 | T-049-011 |
| REQ-TXN-014 | AC-049-012 | T-049-012 |
| REQ-TXN-015 | AC-049-012 | T-049-012 |
| REQ-TXN-016 | AC-049-012 | T-049-012 |

## D1 Defects

없음. 세션 내 수정 사항 없음(초안이 체크리스트 통과).

## 관찰(비차단)

- O1: 실현손익 계산의 수수료 처리(매수 원가 산입 / 매도 대금 차감)를 §5.2 와 수치 앵커(AC-009: 7500)로 명시 — 구현 모호성 제거.
- O2: 통화 환산 제외이나 종목별 분리 집계로 통화 혼동 없음을 §9 에 명시.
- O3: 독립 원장(홀딩스 자동 동기화 없음)은 UX 중복입력 트레이드오프 — §1.1·§2.2 에서 향후 SPEC 으로 명시적 분리.

## 결론

PASS — Run 단계 진입 가능.
