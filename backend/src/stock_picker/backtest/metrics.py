# 백테스트 성과 지표 계산 — CAGR, 최대 낙폭, 샤프 비율
import math
from datetime import date


def calculate_cagr(
    daily_returns: list[float], start_date: date, end_date: date
) -> float:
    """연평균 복합 수익률(CAGR) 계산.

    Args:
        daily_returns: 일별 수익률 목록 (예: [0.01, -0.005, ...])
        start_date: 시작일
        end_date: 종료일

    Returns:
        CAGR (예: 0.15 = 15%)
    """
    if not daily_returns:
        return 0.0

    # 누적 수익률 계산
    cumulative = 1.0
    for r in daily_returns:
        cumulative *= (1.0 + r)

    days = (end_date - start_date).days
    if days <= 0:
        return 0.0

    years = days / 365.25
    if years == 0:
        return 0.0

    # CAGR = (최종값 / 시작값)^(1/연수) - 1
    try:
        cagr = cumulative ** (1.0 / years) - 1.0
    except (ValueError, ZeroDivisionError):
        return 0.0

    return round(cagr, 6)


def calculate_max_drawdown(cumulative_returns: list[float]) -> float:
    """최대 낙폭(Max Drawdown) 계산.

    Args:
        cumulative_returns: 누적 수익률 목록 (예: [1.0, 1.05, 0.95, ...])
            시작값이 1.0인 포트폴리오 가치 시계열

    Returns:
        최대 낙폭 (음수, 예: -0.20 = -20%)
    """
    if not cumulative_returns:
        return 0.0

    max_drawdown = 0.0
    peak = cumulative_returns[0]

    for value in cumulative_returns:
        if value > peak:
            peak = value
        drawdown = (value - peak) / peak if peak > 0 else 0.0
        if drawdown < max_drawdown:
            max_drawdown = drawdown

    return round(max_drawdown, 6)


def calculate_sharpe_ratio(
    daily_returns: list[float], risk_free_rate: float = 0.02
) -> float:
    """샤프 비율(Sharpe Ratio) 계산.

    Args:
        daily_returns: 일별 수익률 목록
        risk_free_rate: 연간 무위험 이자율 (기본값: 2%)

    Returns:
        샤프 비율 (연환산)
    """
    if len(daily_returns) < 2:
        return 0.0

    n = len(daily_returns)
    mean_return = sum(daily_returns) / n

    # 표준편차 계산
    variance = sum((r - mean_return) ** 2 for r in daily_returns) / (n - 1)
    std_dev = math.sqrt(variance)

    if std_dev == 0:
        return 0.0

    # 일별 무위험 이자율로 변환
    daily_risk_free = risk_free_rate / 252.0

    # 연환산 샤프 비율 (√252 스케일링)
    sharpe = (mean_return - daily_risk_free) / std_dev * math.sqrt(252)
    return round(sharpe, 4)
