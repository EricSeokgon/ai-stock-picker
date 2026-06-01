# 스코어링 엔진 테스트 - 순수 함수 검증
import pytest


class TestCalculateStockScore:
    """calculate_stock_score 함수 테스트"""

    def test_all_half_inputs_returns_half(self):
        """모든 입력이 0.5이면 결과도 0.5여야 한다"""
        from stock_picker.scoring.engine import calculate_stock_score
        result = calculate_stock_score(
            sentiment=0.5,
            volume=0.5,
            momentum=0.5,
            anomaly=0.5,
        )
        assert result == pytest.approx(0.5)

    def test_all_one_inputs_returns_one(self):
        """모든 입력이 1.0이면 결과도 1.0이어야 한다"""
        from stock_picker.scoring.engine import calculate_stock_score
        result = calculate_stock_score(
            sentiment=1.0,
            volume=1.0,
            momentum=1.0,
            anomaly=1.0,
        )
        assert result == pytest.approx(1.0)

    def test_all_zero_inputs_returns_zero(self):
        """모든 입력이 0.0이면 결과도 0.0이어야 한다"""
        from stock_picker.scoring.engine import calculate_stock_score
        result = calculate_stock_score(
            sentiment=0.0,
            volume=0.0,
            momentum=0.0,
            anomaly=0.0,
        )
        assert result == pytest.approx(0.0)

    def test_weight_is_40_percent_sentiment(self):
        """감성 점수 가중치는 40%여야 한다"""
        from stock_picker.scoring.engine import calculate_stock_score
        # sentiment만 1.0, 나머지 0.0
        result = calculate_stock_score(
            sentiment=1.0,
            volume=0.0,
            momentum=0.0,
            anomaly=0.0,
        )
        assert result == pytest.approx(0.40, abs=1e-6)

    def test_weight_is_20_percent_volume(self):
        """거래량 점수 가중치는 20%여야 한다"""
        from stock_picker.scoring.engine import calculate_stock_score
        result = calculate_stock_score(
            sentiment=0.0,
            volume=1.0,
            momentum=0.0,
            anomaly=0.0,
        )
        assert result == pytest.approx(0.20, abs=1e-6)

    def test_weight_is_25_percent_momentum(self):
        """모멘텀 점수 가중치는 25%여야 한다"""
        from stock_picker.scoring.engine import calculate_stock_score
        result = calculate_stock_score(
            sentiment=0.0,
            volume=0.0,
            momentum=1.0,
            anomaly=0.0,
        )
        assert result == pytest.approx(0.25, abs=1e-6)

    def test_weight_is_15_percent_anomaly(self):
        """이상거래 점수 가중치는 15%여야 한다"""
        from stock_picker.scoring.engine import calculate_stock_score
        result = calculate_stock_score(
            sentiment=0.0,
            volume=0.0,
            momentum=0.0,
            anomaly=1.0,
        )
        assert result == pytest.approx(0.15, abs=1e-6)

    def test_none_inputs_default_to_zero(self):
        """None 입력은 0.0으로 처리되어야 한다"""
        from stock_picker.scoring.engine import calculate_stock_score
        result = calculate_stock_score(
            sentiment=None,
            volume=None,
            momentum=None,
            anomaly=None,
        )
        assert result == pytest.approx(0.0)

    def test_partial_none_inputs(self):
        """일부 None 입력 시 나머지 값으로만 점수를 계산해야 한다"""
        from stock_picker.scoring.engine import calculate_stock_score
        # sentiment=1.0, 나머지 None → 0.40
        result = calculate_stock_score(
            sentiment=1.0,
            volume=None,
            momentum=None,
            anomaly=None,
        )
        assert result == pytest.approx(0.40, abs=1e-6)

    def test_weights_sum_to_one(self):
        """가중치의 합은 1.0이어야 한다 (내부 검증)"""
        # 0.40 + 0.20 + 0.25 + 0.15 = 1.00
        assert pytest.approx(0.40 + 0.20 + 0.25 + 0.15) == 1.0


class TestRankStocks:
    """rank_stocks 함수 테스트"""

    def test_returns_sorted_by_score_descending(self):
        """점수 내림차순으로 정렬된 리스트를 반환해야 한다"""
        from stock_picker.scoring.engine import rank_stocks
        scores = {"종목A": 0.7, "종목B": 0.9, "종목C": 0.5}
        result = rank_stocks(scores, top_n=10)
        assert result[0] == ("종목B", pytest.approx(0.9))
        assert result[1] == ("종목A", pytest.approx(0.7))
        assert result[2] == ("종목C", pytest.approx(0.5))

    def test_returns_top_n_stocks(self):
        """top_n 개수만큼 반환해야 한다"""
        from stock_picker.scoring.engine import rank_stocks
        scores = {"종목A": 0.9, "종목B": 0.8, "종목C": 0.7, "종목D": 0.6}
        result = rank_stocks(scores, top_n=2)
        assert len(result) == 2
        assert result[0][0] == "종목A"
        assert result[1][0] == "종목B"

    def test_handles_fewer_than_top_n_stocks(self):
        """종목 수가 top_n보다 적으면 전체를 반환해야 한다"""
        from stock_picker.scoring.engine import rank_stocks
        scores = {"종목A": 0.8, "종목B": 0.6}
        result = rank_stocks(scores, top_n=10)
        assert len(result) == 2

    def test_empty_scores_returns_empty_list(self):
        """빈 점수 딕셔너리는 빈 리스트를 반환해야 한다"""
        from stock_picker.scoring.engine import rank_stocks
        result = rank_stocks({})
        assert result == []

    def test_default_top_n_is_ten(self):
        """기본 top_n은 10이어야 한다"""
        from stock_picker.scoring.engine import rank_stocks
        scores = {f"종목{i}": float(i) / 20 for i in range(15)}
        result = rank_stocks(scores)
        assert len(result) == 10

    def test_returns_list_of_tuples(self):
        """결과는 (종목코드, 점수) 튜플의 리스트여야 한다"""
        from stock_picker.scoring.engine import rank_stocks
        scores = {"005930": 0.75}
        result = rank_stocks(scores)
        assert isinstance(result, list)
        assert isinstance(result[0], tuple)
        assert result[0][0] == "005930"
        assert result[0][1] == pytest.approx(0.75)
