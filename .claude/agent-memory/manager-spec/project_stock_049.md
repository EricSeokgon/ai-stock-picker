---
name: project-stock-049
description: SPEC-STOCK-049 포트폴리오 거래 원장 & 실현손익 — 소셜아크(042~048) 후 신규 도메인, 신규 테이블 portfolio_transactions(마이그 0030), 이동평균 원가법, sync 서비스
metadata:
  type: project
---

SPEC-STOCK-049 — 포트폴리오 거래 내역 & 실현손익 (Transaction Ledger & Realized P&L). 소셜 아크(042~048) 완료 후 **신규 도메인** 개설.

**Why:** 기존 전 기능이 현재 보유상태(미실현)만 다룸 — `PortfolioHolding` 은 quantity·avg_buy_price 만 저장, 개별 매수/매도 거래 기록 없음 → **거래 내역·실현손익 부재**. 한국 개인투자자 핵심 니즈(실현손익) 충족. 벤치마크(034)·배당(019/033)·리밸런싱(032)·리스크(027)·성과(030)는 이미 존재 → 이들과 겹치지 않는 유일한 고가치 갭.

**How to apply (구현 시 핵심 제약):**
- **신규 테이블 1개**: `portfolio_transactions` (id, portfolio_id FK CASCADE, krx_code, market default KRX, side BUY/SELL, quantity Integer, price Numeric(10,2), fee Numeric(10,2) default 0, traded_at, created_at) + index(portfolio_id, krx_code). **마이그 0030**(down_revision 0029 — 0029 가 현재 최신).
- **거래 서비스는 sync**(`transactions.py`, `db: Session`) — 기존 `service.add_holding`/`remove_holding` 패턴 준수. async 혼용 금지.
- **이동평균 원가법(총평균)** 단일 방식. FIFO/개별법 로트 제외. BUY: cost += price*qty + fee, pos += qty. SELL: avg=cost/pos; realized += (price*qty − fee) − avg*qty; cost −= avg*qty; pos −= qty (avg 불변). **수치앵커(AC-009)**: BUY10@1000·BUY10@2000·SELL5@3000 → realized=**7500**.
- **매도 검증**: SELL 은 (portfolio_id,krx_code,market) 순보유(누적BUY−누적SELL) 이내만 허용, 초과 거부(REQ-TXN-003).
- **독립 원장**: 거래 기록이 `PortfolioHolding` 자동 갱신 **안 함**. 기존 홀딩스/performance/benchmark 로직 불변. (중복입력 트레이드오프, 자동동기화는 향후 SPEC.)
- **금액 Decimal/Numeric(10,2)** 로 계산(부동소수 오차 회피). 정렬은 traded_at + id 보조키(결정적).
- **엔드포인트**: POST/GET/DELETE `/portfolios/{id}/transactions`, GET `/portfolios/{id}/realized-pnl`. `get_db_session`+`get_current_user`, 소유권 쿼리 확인, HTTPException 404/400/409.
- **제외**: 자동매매(영구), 증권사 연동/임포트, 홀딩스 자동동기화, FIFO, 양도세 계산, 통화환산, 미실현손익(030/034 담당), 배당원장(019/033), 거래 수정(생성·삭제만), 거래 알림, 공개공유 노출.
- **프론트**: `portfolio.ts`(+.js) 거래 API 4종, 거래원장 뷰(.tsx+.js) 폼·목록·전체 실현손익. `.js`/`.ts` 페어 동기화 필수.

REQ 16(REQ-TXN-001~016)·AC 12(AC-049-001~012)·테스트 12(T-049-001~012). 신규 접두사 `REQ-TXN-`. 파일 spec.md 단일. 자체 감사 PASS(D1 0건).
