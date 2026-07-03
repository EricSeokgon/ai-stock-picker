# advice 서비스 단위 테스트 — SPEC-STOCK-014 M2-M5
# RED 단계: 리밸런싱·리스크·브리핑·이력·피드백 서비스 로직 검증
from unittest.mock import MagicMock, patch



class TestBuildHoldingsSummary:
    """보유 종목 요약 데이터 생성 로직"""

    def test_builds_summary_from_holdings(self):
        """보유 종목 목록에서 요약 데이터를 생성해야 한다"""
        from stock_picker.advice.service import build_holdings_summary

        holdings = [
            MagicMock(krx_code="005930", quantity=10, avg_buy_price=70000.0),
            MagicMock(krx_code="000660", quantity=5, avg_buy_price=100000.0),
        ]
        result = build_holdings_summary(holdings)
        assert len(result) == 2
        assert result[0]["krx_code"] == "005930"
        assert result[0]["quantity"] == 10
        assert "invested_amount" in result[0]
        assert "weight_pct" in result[0]

    def test_weight_sums_to_100(self):
        """비중 합계가 100이어야 한다"""
        from stock_picker.advice.service import build_holdings_summary

        holdings = [
            MagicMock(krx_code="005930", quantity=10, avg_buy_price=70000.0),
            MagicMock(krx_code="000660", quantity=10, avg_buy_price=30000.0),
        ]
        result = build_holdings_summary(holdings)
        total_weight = sum(r["weight_pct"] for r in result)
        assert abs(total_weight - 100.0) < 0.01

    def test_empty_holdings_returns_empty_list(self):
        """빈 보유 목록이면 빈 리스트를 반환해야 한다"""
        from stock_picker.advice.service import build_holdings_summary

        result = build_holdings_summary([])
        assert result == []


class TestComputeRiskScore:
    """리스크 점수 계산 로직"""

    def test_high_concentration_gives_high_score(self):
        """단일 종목 집중도가 높으면 리스크 점수가 높아야 한다"""
        from stock_picker.advice.service import compute_risk_score

        # 단일 종목 100% 집중
        holdings_summary = [
            {"krx_code": "005930", "sector": "전자/반도체", "weight_pct": 100.0, "invested_amount": 1000000}
        ]
        score = compute_risk_score(holdings_summary)
        assert score >= 70  # 높은 위험

    def test_diversified_portfolio_gives_lower_score(self):
        """분산된 포트폴리오는 단일 집중 대비 낮은 리스크 점수를 가져야 한다"""
        from stock_picker.advice.service import compute_risk_score

        # 5개 종목 균등 분배 (각 다른 섹터)
        holdings_summary = [
            {"krx_code": f"0{i}0000", "sector": f"섹터{i}", "weight_pct": 20.0, "invested_amount": 200000}
            for i in range(5)
        ]
        score_diversified = compute_risk_score(holdings_summary)

        # 단일 종목 집중과 비교
        holdings_concentrated = [
            {"krx_code": "005930", "sector": "전자/반도체", "weight_pct": 100.0, "invested_amount": 1000000}
        ]
        score_concentrated = compute_risk_score(holdings_concentrated)

        # 분산이 집중보다 낮아야 함
        assert score_diversified < score_concentrated

    def test_score_in_range_0_100(self):
        """리스크 점수는 0~100 범위이어야 한다"""
        from stock_picker.advice.service import compute_risk_score

        holdings_summary = [
            {"krx_code": "005930", "weight_pct": 60.0, "invested_amount": 600000},
            {"krx_code": "000660", "weight_pct": 40.0, "invested_amount": 400000},
        ]
        score = compute_risk_score(holdings_summary)
        assert 0 <= score <= 100

    def test_single_stock_over_50pct_flagged(self):
        """단일 종목이 50% 초과이면 반환 값이 높아야 한다 (REQ-RM-004)"""
        from stock_picker.advice.service import compute_risk_score

        holdings_summary = [
            {"krx_code": "005930", "sector": "전자/반도체", "weight_pct": 60.0, "invested_amount": 600000},
            {"krx_code": "000660", "sector": "전자/반도체", "weight_pct": 40.0, "invested_amount": 400000},
        ]
        score = compute_risk_score(holdings_summary)
        # 60% 단일 종목 노출 → 고위험
        assert score >= 50


class TestExtractJsonFromResponse:
    """Claude 응답에서 JSON 추출 로직"""

    def test_extracts_clean_json(self):
        """깔끔한 JSON 응답을 파싱할 수 있어야 한다"""
        from stock_picker.advice.service import extract_json_from_response

        response = '{"actions": [{"krx_code": "005930", "action": "hold"}]}'
        result = extract_json_from_response(response)
        assert result["actions"][0]["krx_code"] == "005930"

    def test_extracts_json_with_surrounding_text(self):
        """주변 텍스트가 있어도 JSON을 추출할 수 있어야 한다"""
        from stock_picker.advice.service import extract_json_from_response

        response = 'Here is the analysis: {"actions": []} 끝.'
        result = extract_json_from_response(response)
        assert "actions" in result

    def test_returns_error_dict_on_invalid_json(self):
        """유효하지 않은 JSON이면 오류 딕셔너리를 반환해야 한다"""
        from stock_picker.advice.service import extract_json_from_response

        result = extract_json_from_response("not valid json at all")
        assert "error" in result


class TestGenerateRebalancingAdvice:
    """리밸런싱 제안 생성 로직 (Claude mock)"""

    @patch("stock_picker.advice.service._get_api_key", return_value="test-key")
    @patch("stock_picker.advice.service.anthropic.Anthropic")
    def test_returns_advice_dict_with_actions(self, mock_anthropic, mock_key):
        """리밸런싱 조언이 actions 리스트를 포함해야 한다"""
        from stock_picker.advice.service import generate_rebalancing_advice

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_message = MagicMock()
        mock_message.content = [
            MagicMock(text='{"actions": [{"krx_code": "005930", "action": "hold", "reason": "안정적"}]}')
        ]
        mock_client.messages.create.return_value = mock_message

        holdings_summary = [
            {"krx_code": "005930", "weight_pct": 100.0, "invested_amount": 1000000}
        ]
        rec_universe = [
            {"krx_code": "005930", "rank": 1, "total_score": 0.8}
        ]

        result = generate_rebalancing_advice(holdings_summary, rec_universe)
        assert "actions" in result
        assert len(result["actions"]) > 0

    @patch("stock_picker.advice.service._get_api_key", return_value="test-key")
    @patch("stock_picker.advice.service.anthropic.Anthropic")
    def test_returns_error_dict_on_claude_failure(self, mock_anthropic, mock_key):
        """Claude 실패 시 오류 딕셔너리를 반환해야 한다 (예외 비전파)"""
        from stock_picker.advice.service import generate_rebalancing_advice

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API 오류")

        result = generate_rebalancing_advice([], [])
        assert "error" in result


class TestGenerateRiskProfile:
    """리스크 프로파일 생성 로직 (Claude mock)"""

    @patch("stock_picker.advice.service._get_api_key", return_value="test-key")
    @patch("stock_picker.advice.service.anthropic.Anthropic")
    def test_returns_risk_score_and_explanation(self, mock_anthropic, mock_key):
        """리스크 프로파일이 risk_score와 explanation을 포함해야 한다"""
        from stock_picker.advice.service import generate_risk_profile

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="삼성전자가 포트폴리오의 60%를 차지합니다.")]
        mock_client.messages.create.return_value = mock_message

        holdings_summary = [
            {"krx_code": "005930", "sector": "전자/반도체", "weight_pct": 60.0, "invested_amount": 600000},
            {"krx_code": "000660", "sector": "전자/반도체", "weight_pct": 40.0, "invested_amount": 400000},
        ]
        result = generate_risk_profile(holdings_summary)
        assert "risk_score" in result
        assert "explanation" in result
        assert isinstance(result["risk_score"], int)

    @patch("stock_picker.advice.service._get_api_key", return_value="test-key")
    @patch("stock_picker.advice.service.anthropic.Anthropic")
    def test_returns_error_dict_on_claude_failure(self, mock_anthropic, mock_key):
        """Claude 실패 시 오류 딕셔너리를 반환해야 한다"""
        from stock_picker.advice.service import generate_risk_profile

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = RuntimeError("timeout")

        result = generate_risk_profile([])
        assert "error" in result


class TestGenerateMarketBriefing:
    """시장 브리핑 생성 로직 (Claude mock)"""

    @patch("stock_picker.advice.service._get_api_key", return_value="test-key")
    @patch("stock_picker.advice.service.anthropic.Anthropic")
    def test_returns_briefing_text(self, mock_anthropic, mock_key):
        """시장 브리핑이 briefing 필드를 포함해야 한다"""
        from stock_picker.advice.service import generate_market_briefing

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="오늘 시장은 반도체 업종 중심으로 강세입니다.")]
        mock_client.messages.create.return_value = mock_message

        holdings_summary = [{"krx_code": "005930", "weight_pct": 100.0}]
        market_context = {"sentiment_label": "긍정", "sentiment_score": 0.5}

        result = generate_market_briefing(holdings_summary, market_context)
        assert "briefing" in result
        assert len(result["briefing"]) > 0

    @patch("stock_picker.advice.service._get_api_key", return_value="test-key")
    @patch("stock_picker.advice.service.anthropic.Anthropic")
    def test_returns_fallback_on_failure(self, mock_anthropic, mock_key):
        """Claude 실패 시 폴백 메시지를 반환해야 한다 (REQ-MB-005)"""
        from stock_picker.advice.service import generate_market_briefing

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("network error")

        result = generate_market_briefing([], {})
        assert "error" in result or "briefing" in result


class TestDisclaimerPresence:
    """면책 문구 포함 여부 검증"""

    def test_disclaimer_constant_exists(self):
        """_DISCLAIMER 상수가 존재해야 한다"""
        from stock_picker.advice.service import _DISCLAIMER
        assert "투자 권유" in _DISCLAIMER

    def test_disclaimer_not_empty(self):
        """_DISCLAIMER가 비어 있지 않아야 한다"""
        from stock_picker.advice.service import _DISCLAIMER
        assert len(_DISCLAIMER) > 10
