# 포트폴리오 리스크 분석 서비스 (SPEC-STOCK-027)
# dividends.py 패턴 재사용: run_in_executor로 동기 FDR 격리 + Redis TTL 3600s
# scipy 사용 금지 (REQ-RISK-NFR-001) — numpy만 사용
# @MX:NOTE: [AUTO] scipy 의존성 금지 — np.corrcoef, np.cov, np.std만 허용
# @MX:SPEC: SPEC-STOCK-027
import asyncio
import logging
import math
from datetime import datetime
from typing import Any

import numpy as np

from stock_picker.portfolio import fx_rate as fx_rate_module
from stock_picker.portfolio import service as portfolio_service
from stock_picker.portfolio.schemas import HoldingVolatility, RiskAnalysisResult

logger = logging.getLogger(__name__)

_RISK_TTL = 3600  # 1시간


# ──────────────────────────────────────────────────────────────
# 순수 함수 레이어
# ──────────────────────────────────────────────────────────────


def _daily_returns(closes: list[float]) -> np.ndarray:
    """종가 리스트에서 일별 수익률 계산.

    daily_return[t] = (close[t] / close[t-1]) - 1
    """
    if len(closes) < 2:
        return np.array([])
    arr = np.array(closes, dtype=float)
    return (arr[1:] / arr[:-1]) - 1.0


def _align_returns(price_data: dict[str, list[dict]]) -> dict[str, np.ndarray]:
    """날짜 기준 내부 조인(inner join)으로 수익률 시리즈 정렬.

    각 종목의 일별 수익률을 공통 거래일 기준으로 정렬한다.
    공통 거래일이 없는 종목은 빈 배열을 반환한다.
    """
    if not price_data:
        return {}

    # 종목별 {date: close} 딕셔너리 생성
    date_close: dict[str, dict[str, float]] = {}
    for ticker, rows in price_data.items():
        date_close[ticker] = {row["date"]: float(row["close"]) for row in rows}

    # 공통 거래일 계산 (모든 종목이 데이터를 가진 날짜)
    date_sets = [set(dc.keys()) for dc in date_close.values()]
    if not date_sets:
        return {}
    common_dates = sorted(date_sets[0].intersection(*date_sets[1:]))

    if len(common_dates) < 2:
        # 공통 날짜가 2개 미만이면 수익률 계산 불가
        return {ticker: np.array([]) for ticker in price_data}

    result: dict[str, np.ndarray] = {}
    for ticker, dc in date_close.items():
        closes = [dc[d] for d in common_dates]
        result[ticker] = _daily_returns(closes)

    return result


def _correlation_matrix(aligned_returns: dict[str, np.ndarray]) -> dict[str, dict[str, float]]:
    """Pearson 상관계수 행렬 계산.

    공통 거래일이 2개 미만인 종목 쌍은 0.0 반환 (NaN 금지).
    대각선은 1.0.
    """
    tickers = list(aligned_returns.keys())
    n = len(tickers)
    result: dict[str, dict[str, float]] = {t: {} for t in tickers}

    for i in range(n):
        for j in range(n):
            ti, tj = tickers[i], tickers[j]
            ri = aligned_returns[ti]
            rj = aligned_returns[tj]

            if i == j:
                result[ti][tj] = 1.0
                continue

            # 공통 유효 인덱스 (NaN 제거)
            if len(ri) < 2 or len(rj) < 2 or len(ri) != len(rj):
                result[ti][tj] = 0.0
                continue

            try:
                corr_matrix = np.corrcoef(ri, rj)
                val = float(corr_matrix[0, 1])
                # NaN/Inf 가드
                if math.isnan(val) or math.isinf(val):
                    val = 0.0
                # [-1, 1] 클램핑
                val = max(-1.0, min(1.0, val))
                result[ti][tj] = round(val, 4)
            except Exception:
                result[ti][tj] = 0.0

    return result


def _annualized_volatility(returns: np.ndarray) -> float:
    """일별 수익률 배열에서 연환산 변동성 계산.

    annualized_vol = std(daily_returns) × √252 × 100
    """
    if len(returns) < 2:
        return 0.0
    std = float(np.std(returns, ddof=1))
    return std * math.sqrt(252) * 100.0


def _portfolio_volatility(
    weights: np.ndarray,
    aligned_returns: dict[str, np.ndarray],
) -> float:
    """포트폴리오 변동성 계산.

    # @MX:NOTE: [AUTO] 공분산 행렬은 연환산 (np.cov × 252)
    port_vol = sqrt(wᵀ · cov_annualized · w) × √252 × 100
    단, cov가 이미 연환산되었으므로 √252는 cov 내부에 포함됨
    port_vol = sqrt(wᵀ · (np.cov × 252) · w) × 100
    """
    tickers = list(aligned_returns.keys())
    n = len(tickers)

    if n == 0:
        return 0.0

    # 수익률 행렬 구성 (각 행이 종목, 각 열이 거래일)
    returns_matrix = np.array([aligned_returns[t] for t in tickers])

    if returns_matrix.shape[1] < 2:
        return 0.0

    # 연환산 공분산 행렬
    cov_matrix = np.cov(returns_matrix) * 252

    if n == 1:
        # 단일 자산: cov_matrix는 스칼라
        port_var = float(cov_matrix)
    else:
        port_var = float(weights @ cov_matrix @ weights)

    if port_var < 0:
        port_var = 0.0

    return math.sqrt(port_var) * 100.0


def _diversification_benefit(
    port_vol: float,
    weights: np.ndarray,
    vols: list[float],
) -> float:
    """분산 효과 계산.

    diversification_benefit = max(0, (1 - port_vol / weighted_avg_vol) × 100)
    weighted_avg_vol = Σ(weightᵢ × volᵢ)
    """
    weighted_avg_vol = float(np.dot(weights, vols))
    if weighted_avg_vol <= 0:
        return 0.0
    benefit = (1.0 - port_vol / weighted_avg_vol) * 100.0
    return max(0.0, round(benefit, 4))


# ──────────────────────────────────────────────────────────────
# FDR 조회 헬퍼 (동기, 스레드 풀에서 실행)
# ──────────────────────────────────────────────────────────────


def _fetch_stock_prices(krx_code: str, period: int) -> list[dict]:
    """동기 FDR 주가 이력 조회 (스레드 풀에서 실행).

    # @MX:NOTE: [AUTO] 동기 FDR 호출 — run_in_executor에서만 호출할 것
    FDR DataReader로 krx_code의 최근 period일치 종가 데이터를 가져온다.
    실패 시 빈 리스트 반환.
    """
    try:
        import FinanceDataReader as fdr  # noqa: N813
        import pandas as pd

        end = pd.Timestamp.today()
        # period보다 넉넉하게 조회 (영업일 기준이 아닐 수 있으므로 1.5배)
        start = end - pd.Timedelta(days=int(period * 1.5))

        df = fdr.DataReader(krx_code, start=start.strftime("%Y-%m-%d"))
        if df is None or df.empty:
            return []

        # Close 컬럼 확인
        close_col = None
        for col in ("Close", "close", "종가"):
            if col in df.columns:
                close_col = col
                break
        if close_col is None:
            return []

        # 최근 period개 행만 사용
        df = df.tail(period)
        rows = []
        for idx, row in df.iterrows():
            close_val = row[close_col]
            if close_val is None or (
                hasattr(close_val, "__float__") and math.isnan(float(close_val))
            ):
                continue
            rows.append({"date": str(idx)[:10], "close": float(close_val)})
        return rows
    except Exception as e:
        logger.warning("FDR 주가 조회 실패 — krx_code=%s: %s", krx_code, e)
        return []


# ──────────────────────────────────────────────────────────────
# 오케스트레이션 함수
# ──────────────────────────────────────────────────────────────


async def calculate_risk_analysis(
    portfolio_id: int,
    user_id: int,
    db: Any,
    redis: Any,
    period: int = 90,
    refresh: bool = False,
) -> RiskAnalysisResult:
    """포트폴리오 리스크 분석 계산.

    # @MX:ANCHOR: [AUTO] 리스크 분석 서비스 진입점
    # @MX:REASON: router.py, 테스트에서 3곳 이상 참조
    1. 포트폴리오 소유권 확인 (404/403)
    2. Redis 캐시 조회 (refresh=True이면 건너뜀)
    3. FDR 주가 데이터 수집 (run_in_executor, 종목별 병렬)
    4. 실패 종목 제외, 유효 종목 2개 이상 확인
    5. 순수 함수로 리스크 계산
    6. RiskAnalysisResult 구성
    7. Redis setex TTL=3600s 저장
    """
    from fastapi import HTTPException, status

    # 1. 포트폴리오 소유권 확인
    portfolio = portfolio_service.get_portfolio_with_holdings(db, portfolio_id, user_id)
    if portfolio is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="포트폴리오를 찾을 수 없습니다",
        )

    holdings = portfolio.holdings

    # 2. Redis 캐시 조회 (refresh=True이면 건너뜀)
    today = datetime.now().date().isoformat()
    cache_key = f"portfolio_risk:{portfolio_id}:{period}:{today}"

    if not refresh:
        try:
            cached = await redis.get(cache_key)
            if cached:
                return RiskAnalysisResult.model_validate_json(cached)
        except Exception as e:
            logger.warning("Redis 캐시 조회 실패 — FDR fallback: %s", e)

    # 3. FDR 주가 데이터 수집 (run_in_executor)
    loop = asyncio.get_event_loop()
    price_tasks = [
        loop.run_in_executor(None, _fetch_stock_prices, h.krx_code, period) for h in holdings
    ]
    price_results = await asyncio.gather(*price_tasks)

    # 4. 유효 종목 필터링 (데이터가 있는 종목만)
    valid_holdings = []
    valid_price_data: dict[str, list[dict]] = {}

    for h, prices in zip(holdings, price_results):
        if prices and len(prices) >= 2:
            valid_holdings.append(h)
            valid_price_data[h.krx_code] = prices

    if len(valid_holdings) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="리스크 분석에 필요한 유효 보유 종목이 2개 미만입니다",
        )

    # 5. 수익률 정렬 및 순수 함수 계산
    aligned = _align_returns(valid_price_data)

    # # @MX:NOTE: [AUTO] KRW 환산 가중치 — USD 종목은 fx_rate를 곱해 KRW 기준으로 통일
    # USD 보유 종목 여부 확인 후 필요 시 환율 1회 조회
    has_usd = any(getattr(h, "currency", "KRW") == "USD" for h in valid_holdings)
    if has_usd:
        try:
            fx_rate = await fx_rate_module.get_usd_krw_rate(redis)
        except Exception as e:
            logger.warning("환율 조회 실패 — 폴백 환율 사용: %s", e)
            fx_rate = fx_rate_module._FALLBACK_RATE
    else:
        fx_rate = 1.0

    # 가중치 계산 (quantity × avg_buy_price × fx_rate_if_usd, 없으면 균등 배분)
    weights_raw = []
    for h in valid_holdings:
        if h.krx_code in aligned and len(aligned[h.krx_code]) > 0:
            currency = getattr(h, "currency", "KRW") or "KRW"
            rate = fx_rate if currency == "USD" else 1.0
            weights_raw.append(float(h.avg_buy_price) * float(h.quantity) * rate)
        else:
            weights_raw.append(0.0)

    total_weight = sum(weights_raw)
    if total_weight <= 0:
        # 균등 배분 fallback
        weights = np.ones(len(valid_holdings)) / len(valid_holdings)
    else:
        weights = np.array([w / total_weight for w in weights_raw])

    # 유효한 수익률 데이터가 있는 종목만으로 재필터링
    filtered_holdings = []
    filtered_weights_raw = []
    filtered_aligned: dict[str, np.ndarray] = {}

    for h, w in zip(valid_holdings, weights):
        if h.krx_code in aligned and len(aligned[h.krx_code]) >= 2:
            filtered_holdings.append(h)
            currency = getattr(h, "currency", "KRW") or "KRW"
            rate = fx_rate if currency == "USD" else 1.0
            filtered_weights_raw.append(float(h.avg_buy_price) * float(h.quantity) * rate)
            filtered_aligned[h.krx_code] = aligned[h.krx_code]

    if len(filtered_holdings) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="공통 거래일이 부족하여 리스크 분석을 수행할 수 없습니다",
        )

    total_w = sum(filtered_weights_raw)
    if total_w <= 0:
        final_weights = np.ones(len(filtered_holdings)) / len(filtered_holdings)
    else:
        final_weights = np.array([w / total_w for w in filtered_weights_raw])

    # 상관관계 행렬
    corr_matrix = _correlation_matrix(filtered_aligned)

    # 종목별 변동성
    holdings_volatility: list[HoldingVolatility] = []
    vols: list[float] = []

    for h in filtered_holdings:
        ret = filtered_aligned[h.krx_code]
        vol = _annualized_volatility(ret)
        vols.append(vol)

        # 종목명 조회 (DB 모델에서 가져오고, 없으면 코드 사용)
        raw_name = getattr(h, "name", None)
        name = raw_name if isinstance(raw_name, str) and raw_name else h.krx_code

        holdings_volatility.append(
            HoldingVolatility(
                krx_code=h.krx_code,
                name=name,
                annualized_volatility_pct=round(vol, 4),
                price_data_days=len(valid_price_data.get(h.krx_code, [])),
            )
        )

    # 포트폴리오 변동성
    port_vol = _portfolio_volatility(final_weights, filtered_aligned)

    # 분산 효과
    div_benefit = _diversification_benefit(port_vol, final_weights, vols)

    # 6. RiskAnalysisResult 구성
    result = RiskAnalysisResult(
        correlation_matrix=corr_matrix,
        holdings_volatility=holdings_volatility,
        portfolio_volatility_pct=round(port_vol, 4),
        diversification_benefit_pct=round(div_benefit, 4),
        period_days=period,
        calculated_at=datetime.now().replace(microsecond=0),
    )

    # 7. Redis 캐시 저장 (실패해도 결과 반환)
    try:
        await redis.setex(cache_key, _RISK_TTL, result.model_dump_json())
    except Exception as e:
        logger.warning("Redis 캐시 저장 실패 — portfolio_id=%s: %s", portfolio_id, e)

    return result
