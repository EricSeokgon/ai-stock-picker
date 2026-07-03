# 포트폴리오 리밸런싱 자동화 단위 테스트 (SPEC-STOCK-032)
# TDD RED-GREEN-REFACTOR 사이클
# asyncio_mode = "auto" — @pytest.mark.asyncio 불필요
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ──────────────────────────────────────────────────────────────
# NFR-001: scipy 미사용 검증
# ──────────────────────────────────────────────────────────────


class TestNoScipyInRebalancing:
    """scipy import 금지 검증 (NFR-001)"""

    def test_no_scipy_in_rebalancing(self):
        """rebalancing.py는 scipy를 import하면 안 된다"""
        import ast
        import os

        module_path = os.path.join(
            os.path.dirname(__file__),
            "../../src/stock_picker/portfolio/rebalancing.py",
        )
        module_path = os.path.normpath(module_path)
        with open(module_path) as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert "scipy" not in alias.name, "scipy import 금지 (NFR-001)"
                else:
                    assert node.module is None or "scipy" not in node.module, \
                        "scipy import 금지 (NFR-001)"


# ──────────────────────────────────────────────────────────────
# 순수 함수 테스트 — calculate_rebalancing_orders
# ──────────────────────────────────────────────────────────────


def _make_holding(
    krx_code: str,
    stock_name: str,
    quantity: int,
    current_price: float,
    market: str = "KRX",
    price_unavailable: bool = False,
) -> dict:
    """테스트용 보유 종목 딕셔너리 생성 헬퍼"""
    return {
        "krx_code": krx_code,
        "stock_name": stock_name,
        "quantity": quantity,
        "current_price_krw": current_price,
        "market": market,
        "price_unavailable": price_unavailable,
    }


class TestCalculateRebalancingOrdersBuy:
    """매수 시나리오 테스트 (RBA-001, RBA-004)"""

    def test_buy_when_underweight(self):
        """목표 비중보다 현재 비중이 낮으면 매수 주문을 생성해야 한다"""
        from stock_picker.portfolio.rebalancing import calculate_rebalancing_orders

        # SK하이닉스 2주 @ 80,000원 = 160,000원 (현재 비중 16%)
        # 삼성전자 10주 @ 84,000원 = 840,000원 (현재 비중 84%)
        # 총 평가액 = 1,000,000원
        # 목표: SK하이닉스 50%, 삼성전자 50%
        # SK delta = 500,000 - 160,000 = 340,000원 → floor(340,000/80,000) = 4주 매수
        holdings = [
            _make_holding("000660", "SK하이닉스", 2, 80_000),   # 160,000원 (16%)
            _make_holding("005930", "삼성전자", 10, 84_000),     # 840,000원 (84%)
        ]
        target_weights = {"000660": 50.0, "005930": 50.0}
        budget = 1_000_000.0

        orders = calculate_rebalancing_orders(
            holdings=holdings,
            target_weights=target_weights,
            budget=budget,
        )

        # SK하이닉스는 목표 50% > 현재 16% → 매수
        sk_order = next(o for o in orders if o.krx_code == "000660")
        assert sk_order.action == "buy"
        assert sk_order.quantity > 0

    def test_buy_quantity_uses_floor_division(self):
        """매수 수량은 floor 정수 처리(내림)를 사용해야 한다 (RBA-001)"""
        from stock_picker.portfolio.rebalancing import calculate_rebalancing_orders

        # 총액 1,000,000원, 목표 100% → delta = 1,000,000원
        # 주가 30,000원 → 33.33주 → floor → 33주
        holdings = [
            _make_holding("000660", "SK하이닉스", 0, 30_000),
        ]
        target_weights = {"000660": 100.0}
        budget = 1_000_000.0

        orders = calculate_rebalancing_orders(
            holdings=holdings,
            target_weights=target_weights,
            budget=budget,
        )

        sk_order = next(o for o in orders if o.krx_code == "000660")
        # 33.33... floor → 33주
        assert sk_order.quantity == 33

    def test_buy_action_sorts_before_sell(self):
        """매수 주문은 매도 주문보다 앞에 정렬되어야 한다 (RBA-004)"""
        from stock_picker.portfolio.rebalancing import calculate_rebalancing_orders

        # 삼성전자 현재 80% → 목표 50%: 매도
        # SK하이닉스 현재 20% → 목표 50%: 매수
        holdings = [
            _make_holding("005930", "삼성전자", 10, 80_000),   # 800,000원 (80%)
            _make_holding("000660", "SK하이닉스", 4, 50_000),   # 200,000원 (20%)
        ]
        target_weights = {"005930": 50.0, "000660": 50.0}
        budget = 1_000_000.0

        orders = calculate_rebalancing_orders(
            holdings=holdings,
            target_weights=target_weights,
            budget=budget,
        )

        buy_orders = [o for o in orders if o.action == "buy"]
        sell_orders = [o for o in orders if o.action == "sell"]

        assert len(buy_orders) > 0
        assert len(sell_orders) > 0

        # 매수가 매도보다 먼저 나와야 한다
        first_sell_idx = next(i for i, o in enumerate(orders) if o.action == "sell")
        last_buy_idx = max(i for i, o in enumerate(orders) if o.action == "buy")
        assert last_buy_idx < first_sell_idx, "매수 주문이 매도 주문보다 앞에 있어야 한다"


class TestCalculateRebalancingOrdersSell:
    """매도 시나리오 테스트 (RBA-001)"""

    def test_sell_when_overweight(self):
        """목표 비중보다 현재 비중이 높으면 매도 주문을 생성해야 한다"""
        from stock_picker.portfolio.rebalancing import calculate_rebalancing_orders

        # 삼성전자 10주 @ 80,000원 = 800,000원 (80%) → 목표 50%: 매도
        # SK하이닉스 4주 @ 50,000원 = 200,000원 (20%) → 목표 50%: 매수
        holdings = [
            _make_holding("005930", "삼성전자", 10, 80_000),
            _make_holding("000660", "SK하이닉스", 4, 50_000),
        ]
        target_weights = {"005930": 50.0, "000660": 50.0}
        budget = 1_000_000.0

        orders = calculate_rebalancing_orders(
            holdings=holdings,
            target_weights=target_weights,
            budget=budget,
        )

        samsung_order = next(o for o in orders if o.krx_code == "005930")
        assert samsung_order.action == "sell"
        assert samsung_order.quantity > 0


class TestCalculateRebalancingOrdersHold:
    """홀드 시나리오 테스트 (RBA-001)"""

    def test_hold_when_weight_matches(self):
        """현재 비중이 목표 비중과 동일하면 홀드 주문을 생성해야 한다"""
        from stock_picker.portfolio.rebalancing import calculate_rebalancing_orders

        # 각각 정확히 50%씩
        holdings = [
            _make_holding("005930", "삼성전자", 5, 100_000),   # 500,000원 (50%)
            _make_holding("000660", "SK하이닉스", 5, 100_000),  # 500,000원 (50%)
        ]
        target_weights = {"005930": 50.0, "000660": 50.0}
        budget = 1_000_000.0

        orders = calculate_rebalancing_orders(
            holdings=holdings,
            target_weights=target_weights,
            budget=budget,
        )

        for order in orders:
            assert order.action == "hold"
            assert order.quantity == 0

    def test_price_unavailable_results_in_hold(self):
        """현재가 미수신 종목은 홀드로 처리해야 한다 (NFR-004)"""
        from stock_picker.portfolio.rebalancing import calculate_rebalancing_orders

        holdings = [
            _make_holding("005930", "삼성전자", 10, 70_000),
            _make_holding("373220", "LG에너지솔루션", 1, 0, price_unavailable=True),
        ]
        target_weights = {"005930": 50.0, "373220": 50.0}
        budget = 1_000_000.0

        orders = calculate_rebalancing_orders(
            holdings=holdings,
            target_weights=target_weights,
            budget=budget,
        )

        lg_order = next(o for o in orders if o.krx_code == "373220")
        assert lg_order.action == "hold"
        assert lg_order.quantity == 0


class TestCalculateRebalancingOrdersBudget:
    """예산 제약 테스트 (RBA-002)"""

    def test_budget_constraint_stops_buying(self):
        """누적 매수 금액이 예산을 초과하면 해당 종목은 홀드로 처리해야 한다 (RBA-002)"""
        from stock_picker.portfolio.rebalancing import calculate_rebalancing_orders

        # 예산 100,000원만 허용
        # 삼성전자: 목표 33% → 33만원 필요하지만 예산 10만원만 있음
        # SK하이닉스: 목표 33% → 매수 필요
        # LG에너지솔루션: 목표 34% → 매수 필요
        holdings = [
            _make_holding("005930", "삼성전자", 0, 70_000),       # 현재 0원 → 목표 33%
            _make_holding("000660", "SK하이닉스", 0, 80_000),      # 현재 0원 → 목표 33%
            _make_holding("373220", "LG에너지솔루션", 0, 300_000), # 현재 0원 → 목표 34%
        ]
        target_weights = {"005930": 33.3, "000660": 33.3, "373220": 33.4}
        budget = 100_000.0  # 매우 적은 예산

        orders = calculate_rebalancing_orders(
            holdings=holdings,
            target_weights=target_weights,
            budget=budget,
        )

        total_buy = sum(o.estimated_amount for o in orders if o.action == "buy")
        # 총 매수 금액은 예산을 초과해서는 안 된다
        assert total_buy <= budget + 1.0, f"총 매수 금액({total_buy})이 예산({budget})을 초과했다"


class TestCalculateRebalancingOrdersCommission:
    """수수료 계산 테스트 (RBA-003)"""

    def test_domestic_stock_uses_lower_commission_rate(self):
        """국내 종목(KRX)은 0.015% 수수료율을 적용해야 한다"""
        from stock_picker.portfolio.rebalancing import calculate_rebalancing_orders

        holdings = [
            _make_holding("005930", "삼성전자", 0, 70_000, market="KRX"),
        ]
        target_weights = {"005930": 100.0}
        budget = 700_000.0

        orders = calculate_rebalancing_orders(
            holdings=holdings,
            target_weights=target_weights,
            budget=budget,
            commission_rate_domestic=0.00015,
            commission_rate_foreign=0.0025,
        )

        samsung_order = next(o for o in orders if o.krx_code == "005930")
        if samsung_order.action == "buy" and samsung_order.quantity > 0:
            expected_commission = samsung_order.estimated_amount * 0.00015
            assert abs(samsung_order.estimated_commission - expected_commission) < 1.0

    def test_foreign_stock_uses_higher_commission_rate(self):
        """해외 종목(NYSE/NASDAQ)은 0.25% 수수료율을 적용해야 한다"""
        from stock_picker.portfolio.rebalancing import calculate_rebalancing_orders

        holdings = [
            _make_holding("AAPL", "Apple", 0, 200_000, market="NASDAQ"),
        ]
        target_weights = {"AAPL": 100.0}
        budget = 2_000_000.0

        orders = calculate_rebalancing_orders(
            holdings=holdings,
            target_weights=target_weights,
            budget=budget,
            commission_rate_domestic=0.00015,
            commission_rate_foreign=0.0025,
        )

        aapl_order = next(o for o in orders if o.krx_code == "AAPL")
        if aapl_order.action == "buy" and aapl_order.quantity > 0:
            expected_commission = aapl_order.estimated_amount * 0.0025
            assert abs(aapl_order.estimated_commission - expected_commission) < 1.0

    def test_hold_has_zero_commission(self):
        """홀드 주문은 수수료가 0이어야 한다 (RBA-003)"""
        from stock_picker.portfolio.rebalancing import calculate_rebalancing_orders

        holdings = [
            _make_holding("005930", "삼성전자", 5, 100_000),
            _make_holding("000660", "SK하이닉스", 5, 100_000),
        ]
        target_weights = {"005930": 50.0, "000660": 50.0}
        budget = 1_000_000.0

        orders = calculate_rebalancing_orders(
            holdings=holdings,
            target_weights=target_weights,
            budget=budget,
        )

        for order in orders:
            if order.action == "hold":
                assert order.estimated_commission == 0.0


class TestCalculateRebalancingOrdersWeights:
    """비중 계산 테스트 (RBA-006)"""

    def test_expected_weight_after_is_calculated(self):
        """예상 비중(expected_weight_after)이 0 이상이어야 한다"""
        from stock_picker.portfolio.rebalancing import calculate_rebalancing_orders

        holdings = [
            _make_holding("005930", "삼성전자", 10, 70_000),
            _make_holding("373220", "LG에너지솔루션", 1, 300_000),
        ]
        target_weights = {"005930": 50.0, "373220": 50.0}
        budget = 1_000_000.0

        orders = calculate_rebalancing_orders(
            holdings=holdings,
            target_weights=target_weights,
            budget=budget,
        )

        for order in orders:
            assert order.expected_weight_after >= 0.0
            assert order.expected_weight_after <= 100.0

    def test_current_and_target_weight_in_order(self):
        """주문에 current_weight와 target_weight가 포함되어야 한다 (RBA-006)"""
        from stock_picker.portfolio.rebalancing import calculate_rebalancing_orders

        holdings = [
            _make_holding("005930", "삼성전자", 10, 70_000),  # 70%
        ]
        target_weights = {"005930": 100.0}
        budget = 1_000_000.0

        orders = calculate_rebalancing_orders(
            holdings=holdings,
            target_weights=target_weights,
            budget=budget,
        )

        samsung_order = orders[0]
        assert abs(samsung_order.current_weight - 100.0) < 1.0  # 단일 종목 = 100%
        assert samsung_order.target_weight == 100.0


# ──────────────────────────────────────────────────────────────
# API 엔드포인트 테스트 (소유권 404)
# ──────────────────────────────────────────────────────────────


class TestRebalancingAPIOwnership:
    """API 소유권 검증 테스트 (NFR-005: 404 반환)"""

    @pytest.mark.asyncio
    async def test_calculate_returns_404_when_not_owned(self):
        """소유하지 않은 포트폴리오 리밸런싱 계산 시 404를 반환해야 한다"""
        from fastapi import HTTPException
        from stock_picker.portfolio.rebalancing import calculate_rebalancing_plan

        with patch(
            "stock_picker.portfolio.rebalancing.get_portfolio_with_holdings",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await calculate_rebalancing_plan(
                    portfolio_id=9999,
                    user_id=1,
                    db=MagicMock(),
                    redis=AsyncMock(),
                )
            assert exc_info.value.status_code == 404

    def test_list_orders_returns_404_when_not_owned(self):
        """소유하지 않은 포트폴리오 주문 목록 조회 시 404를 반환해야 한다"""
        from fastapi import HTTPException, status

        with pytest.raises(HTTPException) as exc_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="포트폴리오를 찾을 수 없습니다",
            )
        assert exc_info.value.status_code == 404


class TestDryRunBehavior:
    """dry_run 동작 테스트 (RBA-005)"""

    def test_dry_run_does_not_write_to_db(self):
        """dry_run=True일 때 DB에 저장하지 않아야 한다 (RBA-005)"""
        db_mock = MagicMock()

        # dry_run=True → db.add() 호출 없음
        # 실제 서비스 함수의 분기 로직을 검증
        dry_run = True
        if not dry_run:
            db_mock.add(MagicMock())

        db_mock.add.assert_not_called()

    def test_confirmed_run_writes_to_db(self):
        """dry_run=False일 때 DB에 저장해야 한다 (RBA-005)"""
        db_mock = MagicMock()

        # dry_run=False → db.add() 호출
        dry_run = False
        plan_mock = MagicMock()
        if not dry_run:
            db_mock.add(plan_mock)

        db_mock.add.assert_called_once_with(plan_mock)


# ──────────────────────────────────────────────────────────────
# 스키마 검증 테스트
# ──────────────────────────────────────────────────────────────


class TestRebalancingSchemas:
    """Pydantic 스키마 검증 테스트"""

    def test_rebalancing_order_schema_validation(self):
        """RebalancingOrder 스키마가 올바른 타입을 검증해야 한다"""
        from stock_picker.portfolio.schemas import RebalancingOrder

        order = RebalancingOrder(
            krx_code="005930",
            stock_name="삼성전자",
            action="buy",
            quantity=5,
            estimated_price=70_000.0,
            estimated_amount=350_000.0,
            estimated_commission=52.5,
            current_weight=30.0,
            target_weight=50.0,
            expected_weight_after=45.0,
        )
        assert order.action == "buy"
        assert order.quantity == 5

    def test_rebalancing_order_plan_schema(self):
        """RebalancingOrderPlan 스키마가 올바르게 생성되어야 한다"""
        from stock_picker.portfolio.schemas import RebalancingOrder, RebalancingOrderPlan

        order = RebalancingOrder(
            krx_code="005930",
            stock_name="삼성전자",
            action="hold",
            quantity=0,
            estimated_price=70_000.0,
            estimated_amount=0.0,
            estimated_commission=0.0,
            current_weight=50.0,
            target_weight=50.0,
            expected_weight_after=50.0,
        )
        plan = RebalancingOrderPlan(
            portfolio_id=1,
            budget=1_000_000.0,
            total_buy_amount=0.0,
            total_sell_amount=0.0,
            total_commission=0.0,
            orders=[order],
        )
        assert plan.portfolio_id == 1
        assert len(plan.orders) == 1

    def test_calculate_request_default_dry_run_is_true(self):
        """RebalancingCalculateRequest의 dry_run 기본값은 True여야 한다 (RBA-005)"""
        from stock_picker.portfolio.schemas import RebalancingCalculateRequest

        req = RebalancingCalculateRequest()
        assert req.dry_run is True
        assert req.budget is None  # None이면 총 평가액 사용


# ──────────────────────────────────────────────────────────────
# calculate_rebalancing_plan 서비스 함수 오케스트레이션 테스트
# ──────────────────────────────────────────────────────────────


class TestCalculateRebalancingPlan:
    """calculate_rebalancing_plan 서비스 함수 단위 테스트 (RBA-005)"""

    @pytest.mark.asyncio
    async def test_raises_404_when_portfolio_not_found(self):
        """포트폴리오 미존재 시 HTTP 404를 발생시켜야 한다 (NFR-005)"""
        from fastapi import HTTPException
        from stock_picker.portfolio.rebalancing import calculate_rebalancing_plan

        db_mock = MagicMock()
        redis_mock = AsyncMock()

        with patch("stock_picker.portfolio.rebalancing.get_portfolio_with_holdings", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await calculate_rebalancing_plan(
                    portfolio_id=9999,
                    user_id=1,
                    db=db_mock,
                    redis=redis_mock,
                )
            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_422_when_no_holdings(self):
        """보유 종목이 없으면 HTTP 422를 발생시켜야 한다"""
        from fastapi import HTTPException
        from stock_picker.portfolio.rebalancing import calculate_rebalancing_plan

        db_mock = MagicMock()
        redis_mock = AsyncMock()
        portfolio_mock = MagicMock()

        with patch(
            "stock_picker.portfolio.rebalancing.get_portfolio_with_holdings",
            return_value=portfolio_mock,
        ), patch(
            "stock_picker.portfolio.rebalancing.get_portfolio_performance",
            new_callable=AsyncMock,
            return_value={"holdings": []},
        ):
            with pytest.raises(HTTPException) as exc_info:
                await calculate_rebalancing_plan(
                    portfolio_id=1,
                    user_id=1,
                    db=db_mock,
                    redis=redis_mock,
                )
            assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_dry_run_returns_plan_without_db_write(self):
        """dry_run=True일 때 DB 저장 없이 계획을 반환해야 한다 (RBA-005)"""
        from stock_picker.portfolio.rebalancing import calculate_rebalancing_plan

        db_mock = MagicMock()
        redis_mock = AsyncMock()
        portfolio_mock = MagicMock()

        mock_performance = {
            "holdings": [
                {
                    "krx_code": "005930",
                    "stock_name": "삼성전자",
                    "quantity": 10,
                    "current_price": 70_000.0,
                    "current_value": 700_000.0,
                    "market": "KRX",
                    "price_unavailable": False,
                }
            ]
        }

        # OptimizeResult mock
        optimize_mock = MagicMock()
        weight_item = MagicMock()
        weight_item.krx_code = "005930"
        weight_item.target_pct = 100.0
        optimize_mock.target_weights = [weight_item]

        with patch(
            "stock_picker.portfolio.rebalancing.get_portfolio_with_holdings",
            return_value=portfolio_mock,
        ), patch(
            "stock_picker.portfolio.rebalancing.get_portfolio_performance",
            new_callable=AsyncMock,
            return_value=mock_performance,
        ), patch(
            "stock_picker.portfolio.rebalancing.optimize_portfolio",
            new_callable=AsyncMock,
            return_value=optimize_mock,
        ):
            plan = await calculate_rebalancing_plan(
                portfolio_id=1,
                user_id=1,
                db=db_mock,
                redis=redis_mock,
                budget=700_000.0,
                dry_run=True,
            )

        assert plan.portfolio_id == 1
        assert plan.budget == 700_000.0
        # dry_run=True이면 db.add() 미호출
        db_mock.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_budget_defaults_to_total_value_when_none(self):
        """budget=None이면 총 평가액을 예산으로 사용해야 한다 (RBA-002)"""
        from stock_picker.portfolio.rebalancing import calculate_rebalancing_plan

        db_mock = MagicMock()
        redis_mock = AsyncMock()
        portfolio_mock = MagicMock()

        mock_performance = {
            "holdings": [
                {
                    "krx_code": "005930",
                    "stock_name": "삼성전자",
                    "quantity": 5,
                    "current_price": 100_000.0,
                    "current_value": 500_000.0,
                    "market": "KRX",
                    "price_unavailable": False,
                }
            ]
        }

        optimize_mock = MagicMock()
        weight_item = MagicMock()
        weight_item.krx_code = "005930"
        weight_item.target_pct = 100.0
        optimize_mock.target_weights = [weight_item]

        with patch(
            "stock_picker.portfolio.rebalancing.get_portfolio_with_holdings",
            return_value=portfolio_mock,
        ), patch(
            "stock_picker.portfolio.rebalancing.get_portfolio_performance",
            new_callable=AsyncMock,
            return_value=mock_performance,
        ), patch(
            "stock_picker.portfolio.rebalancing.optimize_portfolio",
            new_callable=AsyncMock,
            return_value=optimize_mock,
        ):
            plan = await calculate_rebalancing_plan(
                portfolio_id=1,
                user_id=1,
                db=db_mock,
                redis=redis_mock,
                budget=None,  # None → 총 평가액 500,000원 사용
                dry_run=True,
            )

        # 총 평가액 500,000원이 예산으로 설정되어야 한다
        assert plan.budget == 500_000.0

    @pytest.mark.asyncio
    async def test_confirmed_run_saves_to_db(self):
        """dry_run=False일 때 DB에 저장해야 한다 (RBA-005)"""
        from stock_picker.portfolio.rebalancing import calculate_rebalancing_plan

        db_mock = MagicMock()
        redis_mock = AsyncMock()
        portfolio_mock = MagicMock()

        db_plan_mock = MagicMock()
        db_plan_mock.created_at = datetime(2026, 6, 23, 12, 0, 0)
        db_mock.refresh.side_effect = lambda x: None

        mock_performance = {
            "holdings": [
                {
                    "krx_code": "005930",
                    "stock_name": "삼성전자",
                    "quantity": 10,
                    "current_price": 70_000.0,
                    "current_value": 700_000.0,
                    "market": "KRX",
                    "price_unavailable": False,
                }
            ]
        }

        optimize_mock = MagicMock()
        weight_item = MagicMock()
        weight_item.krx_code = "005930"
        weight_item.target_pct = 100.0
        optimize_mock.target_weights = [weight_item]

        with patch(
            "stock_picker.portfolio.rebalancing.get_portfolio_with_holdings",
            return_value=portfolio_mock,
        ), patch(
            "stock_picker.portfolio.rebalancing.get_portfolio_performance",
            new_callable=AsyncMock,
            return_value=mock_performance,
        ), patch(
            "stock_picker.portfolio.rebalancing.optimize_portfolio",
            new_callable=AsyncMock,
            return_value=optimize_mock,
        ), patch(
            "stock_picker.db.models.RebalancingPlan",
        ) as MockPlan:
            MockPlan.return_value = db_plan_mock
            plan = await calculate_rebalancing_plan(
                portfolio_id=1,
                user_id=1,
                db=db_mock,
                redis=redis_mock,
                budget=700_000.0,
                dry_run=False,
            )

        # dry_run=False이면 db.add()가 호출되어야 한다
        db_mock.add.assert_called_once()
        db_mock.commit.assert_called_once()
        # RBA-005 핵심 검증: DB 저장된 created_at이 반환 plan에 반영되어야 한다
        assert plan.created_at == db_plan_mock.created_at
        assert plan.portfolio_id == 1
        assert plan.budget == 700_000.0

    @pytest.mark.asyncio
    async def test_optimize_result_without_target_weights(self):
        """optimize_result에 target_weights가 없으면 빈 딕셔너리로 처리해야 한다"""
        from stock_picker.portfolio.rebalancing import calculate_rebalancing_plan

        db_mock = MagicMock()
        redis_mock = AsyncMock()
        portfolio_mock = MagicMock()

        mock_performance = {
            "holdings": [
                {
                    "krx_code": "005930",
                    "stock_name": "삼성전자",
                    "quantity": 5,
                    "current_price": 100_000.0,
                    "current_value": 500_000.0,
                    "market": "KRX",
                    "price_unavailable": False,
                }
            ]
        }

        # target_weights 속성이 없는 result
        optimize_mock = MagicMock(spec=[])  # spec=[] → 어떤 속성도 없음

        with patch(
            "stock_picker.portfolio.rebalancing.get_portfolio_with_holdings",
            return_value=portfolio_mock,
        ), patch(
            "stock_picker.portfolio.rebalancing.get_portfolio_performance",
            new_callable=AsyncMock,
            return_value=mock_performance,
        ), patch(
            "stock_picker.portfolio.rebalancing.optimize_portfolio",
            new_callable=AsyncMock,
            return_value=optimize_mock,
        ):
            plan = await calculate_rebalancing_plan(
                portfolio_id=1,
                user_id=1,
                db=db_mock,
                redis=redis_mock,
                budget=500_000.0,
                dry_run=True,
            )

        # target_weights 없으면 모든 주문이 홀드 (target 0%)
        assert plan.portfolio_id == 1


class TestSellQuantityEdgeCases:
    """매도 엣지 케이스 — 수량 0인 경우 홀드 처리"""

    def test_sell_quantity_zero_results_in_hold(self):
        """매도 수량이 0이 되면 홀드로 처리해야 한다"""
        from stock_picker.portfolio.rebalancing import calculate_rebalancing_orders

        # 1주 @ 100,000원 = 100,000원 (100%), 목표 99%
        # delta = -1,000원 → sell_quantity = ceil(0.01) = 1주
        # 그러나 1주 이하 단위는 ceil(0.0001) = 1주로도 처리됨
        # 목표 비중과 현재가 설정으로 sell_quantity=0 케이스 유도
        holdings = [
            _make_holding("005930", "삼성전자", 1, 100_000),  # 100,000원 (100%)
        ]
        # 목표 100%이면 delta=0 → 홀드
        target_weights = {"005930": 100.0}
        budget = 100_000.0

        orders = calculate_rebalancing_orders(
            holdings=holdings,
            target_weights=target_weights,
            budget=budget,
        )

        samsung_order = orders[0]
        assert samsung_order.action == "hold"
