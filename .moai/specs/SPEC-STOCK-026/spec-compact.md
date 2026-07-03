# SPEC-STOCK-026 (Compact) — 포트폴리오 AI 최적화

> Run 단계용 압축본. 요구사항 + 인수 기준만 포함.

## 핵심
서술형 포트폴리오 AI 분석 → 처방형 업그레이드. score(0-100) + 목표비중 + 리밸런싱 액션(매수/매도/유지 + 주수) + 신규 추천 종목 + AsyncAnthropic 전환.
신규 DB 마이그레이션 없음. 모델 `claude-haiku-4-5`, `max_tokens=1024`.

## 수정 파일
- `backend/src/stock_picker/portfolio/ai_analysis.py` (async 전환 + optimize Claude 호출)
- `backend/src/stock_picker/portfolio/service.py` (optimize_portfolio)
- `backend/src/stock_picker/portfolio/schemas.py` (OptimizeResult 등)
- `backend/src/stock_picker/portfolio/router.py` (POST /{id}/optimize)
- `frontend/src/api/portfolio.ts` (optimizePortfolio)
- `frontend/src/pages/Portfolio.tsx` (AI 최적화 탭)
- `frontend/src/components/{PortfolioScoreCard,RebalancingTable,NewStockSuggestions}.tsx` (신규)
- `backend/tests/unit/test_portfolio_optimize.py` (신규)

## 출력 스키마 (OptimizeResult)
- `score`: int 0-100 (= score_breakdown 3값 평균)
- `score_breakdown`: { diversification, risk_balance, momentum } 각 int 0-100
- `target_weights`: [{ krx_code, current_pct, target_pct, action: "buy"|"sell"|"hold", delta_shares: int }]
- `new_stocks`: [{ krx_code, name, sector, reason }] (최대 5, 미보유, recommendations 상위)
- `summary`: str (한국어 3-4문장, 면책 포함)

## 요구사항 (EARS)
- REQ-OPT-001: WHEN POST /portfolios/{id}/optimize THEN score(0-100)+target_weights+new_stocks+summary, 10초 이내.
- REQ-OPT-002: WHERE target_pct > current_pct +2%p THEN action="buy".
- REQ-OPT-003: WHERE target_pct < current_pct -2%p THEN action="sell".
- REQ-OPT-ACTION-001: WHERE |target_pct - current_pct| <= 2%p THEN action="hold".
- REQ-OPT-ACTION-002: delta_shares = buy>0 / sell<0 / hold=0.
- REQ-OPT-004: WHEN 캐시 존재 AND ?refresh=false THEN Claude 호출 없이 캐시 반환.
- REQ-OPT-005: WHERE Anthropic 사용 THEN AsyncAnthropic (동기 Anthropic 금지).
- REQ-OPT-006: WHEN new_stocks 산출 THEN 보유 종목 제외.
- REQ-OPT-007: WHEN score_breakdown 산출 THEN 각 0-100 AND 평균=score.
- REQ-OPT-CONSTRAINT-001: 제약(단일 종목 30%, 단일 섹터 40%)을 프롬프트에 포함.
- REQ-OPT-CONSTRAINT-002: new_stocks = recommendations 상위 미보유 최대 5개.
- REQ-OPT-DATA-001: 입력 = 보유 종목 sector·weight_pct·current_price·최신 추천점수(recommendations 조인).
- REQ-OPT-DATA-002: 보유 종목 없으면 Claude 미호출.
- REQ-OPT-NFR-001: claude-haiku-4-5, max_tokens=1024.
- REQ-OPT-NFR-002: JSON 파싱 실패 시 예외 비전파.
- REQ-OPT-NFR-003: 캐시 적중 시 Claude 호출 0회.

## 캐시
- 키: `portfolio_optimize:{portfolio_id}:{date}`, TTL 3600s, `?refresh=true` 강제 갱신.
- redis.asyncio(api/deps.py) 재사용, graceful degradation.

## 인수 기준
- AC-1 전체 스키마 반환 / AC-2 target_pct 합 ~100% / AC-3 action 방향 / AC-4 캐시(호출 0회) / AC-5 AsyncAnthropic / AC-6 new_stocks 중복제외 ≤5 / AC-7 score 0-100 & breakdown 평균=score / AC-8 기존 ai-analysis async / AC-9 빈 포트폴리오.

## 테스트 (7 필수)
test_optimize_score_range, test_optimize_target_weights_sum_100, test_optimize_action_direction, test_optimize_new_stocks_not_in_portfolio, test_optimize_redis_cache_hit, test_optimize_async_client, test_existing_ai_analysis_async.

## 데이터 출처 정정
"daily_recommendations" → 실제 `recommendations` 테이블(db/models.py Recommendation, total_score·trade_date). 최신 trade_date 기준 조회.

## 제외
scipy/MPT · Monte Carlo · VaR/Sharpe · 세금/거래비용 · 해외자산(SPEC-028) · 상관관계 매트릭스(SPEC-027) · 버전 히스토리 · 실시간 스트리밍 · 자동매매 · 신규 마이그레이션.
