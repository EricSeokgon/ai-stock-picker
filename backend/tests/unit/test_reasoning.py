# 추천 근거 생성 테스트 - 한국어 설명 생성 검증


class TestGenerateReasoning:
    """generate_reasoning 함수 테스트"""

    def test_returns_korean_string(self):
        """한국어 추천 근거 문자열을 반환해야 한다"""
        from stock_picker.scoring.reasoning import generate_reasoning
        result = generate_reasoning(
            krx_code="005930",
            sentiment_score=0.7,
            volume_score=0.5,
            momentum_score=0.6,
            anomaly_score=0.3,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_mentions_dominant_factor_sentiment(self):
        """감성 점수가 가장 높을 때 감성 관련 내용을 포함해야 한다"""
        from stock_picker.scoring.reasoning import generate_reasoning
        result = generate_reasoning(
            krx_code="005930",
            sentiment_score=0.9,
            volume_score=0.1,
            momentum_score=0.1,
            anomaly_score=0.1,
        )
        # 감성 관련 키워드 포함 여부 확인
        assert any(keyword in result for keyword in ["감성", "뉴스", "긍정", "positive"])

    def test_mentions_dominant_factor_volume(self):
        """거래량 점수가 가장 높을 때 거래량 관련 내용을 포함해야 한다"""
        from stock_picker.scoring.reasoning import generate_reasoning
        result = generate_reasoning(
            krx_code="005930",
            sentiment_score=0.1,
            volume_score=0.9,
            momentum_score=0.1,
            anomaly_score=0.1,
        )
        assert any(keyword in result for keyword in ["거래량", "volume", "거래"])

    def test_mentions_dominant_factor_momentum(self):
        """모멘텀 점수가 가장 높을 때 모멘텀 관련 내용을 포함해야 한다"""
        from stock_picker.scoring.reasoning import generate_reasoning
        result = generate_reasoning(
            krx_code="005930",
            sentiment_score=0.1,
            volume_score=0.1,
            momentum_score=0.9,
            anomaly_score=0.1,
        )
        assert any(keyword in result for keyword in ["모멘텀", "momentum", "상승"])

    def test_mentions_dominant_factor_anomaly(self):
        """이상거래 점수가 가장 높을 때 이상거래 관련 내용을 포함해야 한다"""
        from stock_picker.scoring.reasoning import generate_reasoning
        result = generate_reasoning(
            krx_code="005930",
            sentiment_score=0.1,
            volume_score=0.1,
            momentum_score=0.1,
            anomaly_score=0.9,
        )
        assert any(keyword in result for keyword in ["이상", "anomaly", "급등"])

    def test_includes_article_summary_when_provided(self):
        """기사 요약이 제공되면 결과에 포함해야 한다"""
        from stock_picker.scoring.reasoning import generate_reasoning
        summary = "삼성전자, 반도체 수출 급증으로 실적 개선 기대"
        result = generate_reasoning(
            krx_code="005930",
            sentiment_score=0.8,
            volume_score=0.5,
            momentum_score=0.6,
            anomaly_score=0.3,
            top_article_summary=summary,
        )
        # 요약 내용의 일부가 포함되어야 함
        assert summary in result or "삼성전자" in result or "반도체" in result

    def test_works_without_article_summary(self):
        """기사 요약 없이도 추천 근거를 생성해야 한다"""
        from stock_picker.scoring.reasoning import generate_reasoning
        result = generate_reasoning(
            krx_code="005930",
            sentiment_score=0.7,
            volume_score=0.5,
            momentum_score=0.6,
            anomaly_score=0.3,
            top_article_summary=None,
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_includes_krx_code(self):
        """KRX 종목코드가 결과에 포함되어야 한다"""
        from stock_picker.scoring.reasoning import generate_reasoning
        result = generate_reasoning(
            krx_code="005930",
            sentiment_score=0.7,
            volume_score=0.5,
            momentum_score=0.6,
            anomaly_score=0.3,
        )
        assert "005930" in result

    def test_includes_score_value(self):
        """점수 값이 결과에 표시되어야 한다"""
        from stock_picker.scoring.reasoning import generate_reasoning
        result = generate_reasoning(
            krx_code="005930",
            sentiment_score=0.72,
            volume_score=0.5,
            momentum_score=0.6,
            anomaly_score=0.3,
        )
        # 소수점 점수 값이 포함되어야 함
        assert "0.72" in result or "0.7" in result or "72" in result
