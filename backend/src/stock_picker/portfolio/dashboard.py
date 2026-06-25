# 대시보드 순수 함수 모듈 (SPEC-STOCK-038)
# 주의: scipy 사용 금지 — numpy 및 표준 산술 연산만 허용
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

# 허용 기간 상수 (서버 측 검증에 사용)
ALLOWED_DAYS: frozenset[int] = frozenset({7, 30, 90, 365})


# @MX:ANCHOR: [AUTO] filter_snapshots_by_range — 기간별 스냅샷 필터 순수 함수
# @MX:REASON: [AUTO] 엔드포인트 3곳(value-series, sector-summary, asset-allocation)에서 호출 (SPEC-STOCK-038)
def filter_snapshots_by_range(snapshots: list[dict], days: int) -> list[dict]:
    """days 이전부터 현재까지의 스냅샷을 필터링하여 날짜 오름차순으로 반환.

    Args:
        snapshots: 스냅샷 목록. 각 항목은 {date: date, total_value_krw: float} 형태.
        days: 필터링할 기간(일). 현재 날짜에서 days일 이전부터 포함.

    Returns:
        날짜 오름차순으로 정렬된 필터링된 스냅샷 목록.
    """
    if not snapshots:
        return []

    cutoff = date.today() - timedelta(days=days)
    filtered = [s for s in snapshots if s["date"] >= cutoff]
    return sorted(filtered, key=lambda s: s["date"])


# @MX:ANCHOR: [AUTO] aggregate_by_sector — 섹터별 집계 순수 함수
# @MX:REASON: [AUTO] sector-summary 엔드포인트의 핵심 집계 로직 (SPEC-STOCK-038)
def aggregate_by_sector(holdings: list[dict]) -> list[dict]:
    """보유 종목을 섹터별로 집계하여 평가액과 수익률을 계산.

    Args:
        holdings: 보유 종목 목록. 각 항목은 {sector: str|None, current_value: float, cost: float} 형태.
                  섹터가 None이면 '기타/해외'로 분류.

    Returns:
        [{sector: str, value_krw: float, return_pct: float}] 형태의 목록.
        return_pct는 (현재가치 - 비용) / 비용 * 100.
    """
    if not holdings:
        return []

    # 섹터별 집계 딕셔너리
    sector_value: dict[str, float] = defaultdict(float)
    sector_cost: dict[str, float] = defaultdict(float)

    for h in holdings:
        sector = h["sector"] if h["sector"] is not None else "기타/해외"
        sector_value[sector] += h["current_value"]
        sector_cost[sector] += h["cost"]

    result = []
    for sector, value_krw in sector_value.items():
        cost = sector_cost[sector]
        # 비용이 0인 경우 수익률 0으로 처리
        return_pct = ((value_krw - cost) / cost * 100) if cost > 0 else 0.0
        result.append({
            "sector": sector,
            "value_krw": value_krw,
            "return_pct": return_pct,
        })

    return result


# @MX:ANCHOR: [AUTO] aggregate_by_asset_type — 자산유형 배분 순수 함수
# @MX:REASON: [AUTO] asset-allocation 엔드포인트의 핵심 집계 로직 (SPEC-STOCK-038)
def aggregate_by_asset_type(holdings: list[dict]) -> list[dict]:
    """보유 종목을 자산유형별로 집계하여 평가액과 비중을 계산.

    Args:
        holdings: 보유 종목 목록. 각 항목은 {market: str, current_value: float} 형태.
                  KRX → '국내', NYSE/NASDAQ → '해외'.

    Returns:
        [{asset_type: str, value_krw: float, weight_pct: float}] 형태의 목록.
        weight_pct 합계 = 100.
    """
    if not holdings:
        return []

    # 자산유형 분류: KRX → 국내, 그 외 → 해외
    type_value: dict[str, float] = defaultdict(float)

    for h in holdings:
        asset_type = "국내" if h["market"] == "KRX" else "해외"
        type_value[asset_type] += h["current_value"]

    total_value = sum(type_value.values())

    result = []
    for asset_type, value_krw in type_value.items():
        # 총 가치가 0인 경우 0%로 처리
        weight_pct = (value_krw / total_value * 100) if total_value > 0 else 0.0
        result.append({
            "asset_type": asset_type,
            "value_krw": value_krw,
            "weight_pct": weight_pct,
        })

    return result
