# SPEC-STOCK-026 구현 계획 (Implementation Plan)

> 포트폴리오 AI 최적화 — 서술형 → 처방형 업그레이드.

## 마일스톤 분해 (Milestone Decomposition)

### M1 — 백엔드 최적화 서비스 (Priority: High)

ai_analysis.py async 전환 + optimize 함수 + schemas + service + router를 한 단위로 구현한다.

| 태스크 | 파일 | 내용 |
|--------|------|------|
| T1-1 | `portfolio/ai_analysis.py` | `anthropic.Anthropic()` → `anthropic.AsyncAnthropic()` 전환. 호출부 `await client.messages.create(...)`. `@MX:WARN` 제거. `analyze_portfolio()` async화. |
| T1-2 | `portfolio/service.py` | `optimize_portfolio(portfolio_id, user_id, db, refresh=False)` 서비스 로직. 보유 종목 + sector + weight_pct + current_price 수집(SPEC-017 재사용), `recommendations` 최신 trade_date 점수 조인, 미보유 추천 후보 추출, Claude 호출, action/delta_shares 서버측 보정. |
| T1-3 | `portfolio/schemas.py` | `TargetWeightItem`·`NewStockItem`·`ScoreBreakdown`·`OptimizeResult` 스키마. |
| T1-4 | `portfolio/router.py` | `POST /portfolios/{portfolio_id}/optimize?refresh={bool}` (async, 인증·소유권 404). |

**완료 기준**: optimize 엔드포인트가 score(0-100)·target_weights·new_stocks·summary를 반환하며, 포트폴리오 모듈에서 동기 Anthropic 클래스가 완전히 제거됨.

### M2 — Redis 캐싱 (Priority: Medium)

| 태스크 | 파일 | 내용 |
|--------|------|------|
| T2-1 | `portfolio/service.py` | optimize Redis 캐시 레이어. 키 `portfolio_optimize:{portfolio_id}:{date}`, TTL 3600s, `?refresh=true` 시 무시·재계산. graceful degradation. |

**완료 기준**: `?refresh=false` + 캐시 존재 시 Claude API 호출 0회.

### M3 — 프론트엔드 최적화 UI (Priority: Medium)

| 태스크 | 파일 | 내용 |
|--------|------|------|
| T3-1 | `frontend/src/api/portfolio.ts` | `optimizePortfolio(portfolioId, refresh?)` 함수. |
| T3-2 | `frontend/src/components/PortfolioScoreCard.tsx` | 원형 점수(0-100) + 분해 막대. |
| T3-3 | `frontend/src/components/RebalancingTable.tsx` | krx_code/현재비중/목표비중/액션/주수 테이블. |
| T3-4 | `frontend/src/components/NewStockSuggestions.tsx` | 추가 추천 종목(최대 5개). |
| T3-5 | `frontend/src/pages/Portfolio.tsx` | "AI 최적화 분석" 탭 추가(기존 섹션 보존). |

**완료 기준**: AI 최적화 탭에서 점수·리밸런싱·신규추천 3개 컴포넌트가 렌더링됨.

### M4 — 기존 AI 분석 async 전환 (Priority: High, 버그 수정)

> M1 T1-1에 통합되어 함께 수행됨. `POST /portfolios/{id}/ai-analysis`가 async 클라이언트를 사용하도록 보장. (별도 마일스톤으로 추적하되 구현은 T1-1과 동일 커밋 가능.)

**완료 기준**: `ai_analysis.py` 어디에서도 `anthropic.Anthropic(`(동기)가 사용되지 않고, ai-analysis 엔드포인트도 `async def`.

### M5 — 단위 테스트 (Priority: Medium)

| 태스크 | 파일 | 내용 |
|--------|------|------|
| T5-1 | `backend/tests/unit/test_portfolio_optimize.py` | 7개 테스트: score 범위·target 합계·action 방향·new_stocks 중복제외·캐시 적중·AsyncAnthropic 사용·기존 분석 async. |

**완료 기준**: 7개 테스트 통과, 커버리지 fail_under=85 충족.

---

## 기술 접근 요약 (Technical Approach)

- **Claude 호출**: `claude-haiku-4-5`(비용 유지) + `max_tokens=1024`(확장) + `AsyncAnthropic`. 기존 `analysis/client.py`·`ai_analysis.py` 패턴 재사용.
- **입력 데이터**: 보유 종목(quantity·avg_buy_price·sector) + 현재가 + 비중% + 최신 추천 점수(`recommendations` 조인). 미보유 추천 상위 종목 후보.
- **제약 조건**: 단일 종목 ≤30%, 단일 섹터 ≤40% (Claude 프롬프트에 명시).
- **사후 검증**: Claude가 반환한 target_pct로부터 action(2%p 임계)·delta_shares를 서버에서 재계산·보정하여 REQ-OPT-002/003/ACTION-001/002 보장.
- **캐싱**: Redis(redis.asyncio, api/deps.py), 키 `portfolio_optimize:{id}:{date}`, TTL 3600s.

---

## 리스크 및 완화 (Risks & Mitigation)

| 리스크 | 영향 | 완화 |
|--------|------|------|
| **Claude 응답 JSON 파싱 실패** | 최적화 결과 손상 | 엄격 JSON 출력 지시 + 파싱 실패 시 예외 비전파(REQ-OPT-NFR-002), 오류 마커 응답. 서버측 스키마 검증. |
| **AsyncAnthropic in FastAPI** | 이벤트 루프 호환성 | 모든 호출부 `await`. 라우터·서비스 함수 async화. 기존 `analysis/client.py`(AsyncAnthropic)가 동일 패턴으로 이미 검증됨. |
| **target_pct 합계 부정확** | 비중 합계 ≠ 100% | 서버측 정규화 또는 합계 검증(AC-2). 합계 ~100%(±오차) 허용. |
| **추천 데이터 부재(preparing)** | new_stocks 비어 있음 | `recommendations` 미적재 시 new_stocks 빈 리스트 graceful 처리. |
| **score_breakdown 평균 ≠ score** | REQ-OPT-007 위반 | score를 breakdown 평균으로 서버에서 강제 계산(Claude 값 신뢰하지 않음). |

---

## MX 태그 대상

- `optimize_portfolio()` — 외부 API(Claude) 호출 + fan_in 가능 → `@MX:NOTE` 또는 `@MX:ANCHOR`.
- `ai_analysis.py` 기존 `@MX:WARN`(동기 호출) → async 전환으로 **제거**.
