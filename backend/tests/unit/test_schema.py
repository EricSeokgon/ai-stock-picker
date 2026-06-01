# Claude API 출력 스키마 검증 테스트 - Pydantic v2 유효성 검사
import pytest
from pydantic import ValidationError


class TestClaudeAnalysisOutputValid:
    """유효한 입력에 대한 ClaudeAnalysisOutput 검증 테스트"""

    def test_valid_full_input_succeeds(self):
        """모든 필드가 유효한 경우 검증을 통과해야 한다"""
        from stock_picker.analysis.schema import ClaudeAnalysisOutput
        data = {
            "sentiment": "positive",
            "sentiment_score": 0.72,
            "sector_tags": ["반도체", "IT"],
            "keywords": ["삼성전자", "수출", "실적"],
            "summary": "삼성전자 반도체 수출 급증으로 3분기 실적 개선 기대.",
        }
        result = ClaudeAnalysisOutput(**data)
        assert result.sentiment == "positive"
        assert result.sentiment_score == pytest.approx(0.72)

    def test_empty_sector_tags_is_valid(self):
        """sector_tags가 빈 배열이어도 유효해야 한다"""
        from stock_picker.analysis.schema import ClaudeAnalysisOutput
        data = {
            "sentiment": "neutral",
            "sentiment_score": 0.0,
            "sector_tags": [],  # 빈 배열 허용
            "keywords": ["경제"],
            "summary": "중립적인 경제 지표 발표.",
        }
        result = ClaudeAnalysisOutput(**data)
        assert result.sector_tags == []

    def test_negative_sentiment_score_boundary(self):
        """sentiment_score 최솟값 -1.0은 유효해야 한다"""
        from stock_picker.analysis.schema import ClaudeAnalysisOutput
        data = {
            "sentiment": "negative",
            "sentiment_score": -1.0,
            "sector_tags": [],
            "keywords": ["하락"],
            "summary": "시장 급락으로 투자심리 악화.",
        }
        result = ClaudeAnalysisOutput(**data)
        assert result.sentiment_score == pytest.approx(-1.0)

    def test_positive_sentiment_score_boundary(self):
        """sentiment_score 최댓값 1.0은 유효해야 한다"""
        from stock_picker.analysis.schema import ClaudeAnalysisOutput
        data = {
            "sentiment": "positive",
            "sentiment_score": 1.0,
            "sector_tags": ["IT"],
            "keywords": ["호실적"],
            "summary": "역대 최고 실적 달성.",
        }
        result = ClaudeAnalysisOutput(**data)
        assert result.sentiment_score == pytest.approx(1.0)

    def test_all_sentiment_values_valid(self):
        """positive, negative, neutral 모두 유효해야 한다"""
        from stock_picker.analysis.schema import ClaudeAnalysisOutput
        base = {
            "sentiment_score": 0.0,
            "sector_tags": [],
            "keywords": ["테스트"],
            "summary": "테스트 요약.",
        }
        for sentiment in ["positive", "negative", "neutral"]:
            data = {**base, "sentiment": sentiment}
            result = ClaudeAnalysisOutput(**data)
            assert result.sentiment == sentiment


class TestClaudeAnalysisOutputInvalid:
    """유효하지 않은 입력에 대한 ClaudeAnalysisOutput 검증 테스트"""

    def test_missing_sentiment_raises_validation_error(self):
        """sentiment 필드 누락 시 ValidationError를 발생시켜야 한다"""
        from stock_picker.analysis.schema import ClaudeAnalysisOutput
        data = {
            "sentiment_score": 0.5,
            "sector_tags": [],
            "keywords": ["테스트"],
            "summary": "테스트.",
        }
        with pytest.raises(ValidationError):
            ClaudeAnalysisOutput(**data)

    def test_invalid_sentiment_value_raises_validation_error(self):
        """sentiment이 허용값(positive/negative/neutral) 외 값이면 ValidationError를 발생시켜야 한다"""
        from stock_picker.analysis.schema import ClaudeAnalysisOutput
        data = {
            "sentiment": "bullish",  # 허용되지 않는 값
            "sentiment_score": 0.5,
            "sector_tags": [],
            "keywords": ["테스트"],
            "summary": "테스트.",
        }
        with pytest.raises(ValidationError):
            ClaudeAnalysisOutput(**data)

    def test_sentiment_score_above_1_raises_validation_error(self):
        """sentiment_score가 1.0 초과이면 ValidationError를 발생시켜야 한다"""
        from stock_picker.analysis.schema import ClaudeAnalysisOutput
        data = {
            "sentiment": "positive",
            "sentiment_score": 1.001,  # 범위 초과
            "sector_tags": [],
            "keywords": ["테스트"],
            "summary": "테스트.",
        }
        with pytest.raises(ValidationError):
            ClaudeAnalysisOutput(**data)

    def test_sentiment_score_below_minus_1_raises_validation_error(self):
        """sentiment_score가 -1.0 미만이면 ValidationError를 발생시켜야 한다"""
        from stock_picker.analysis.schema import ClaudeAnalysisOutput
        data = {
            "sentiment": "negative",
            "sentiment_score": -1.001,  # 범위 미만 (E-6 케이스)
            "sector_tags": [],
            "keywords": ["하락"],
            "summary": "테스트.",
        }
        with pytest.raises(ValidationError):
            ClaudeAnalysisOutput(**data)

    def test_keywords_as_non_list_raises_validation_error(self):
        """keywords가 리스트가 아니면 ValidationError를 발생시켜야 한다"""
        from stock_picker.analysis.schema import ClaudeAnalysisOutput
        data = {
            "sentiment": "neutral",
            "sentiment_score": 0.0,
            "sector_tags": [],
            "keywords": "단일문자열",  # 리스트가 아닌 문자열
            "summary": "테스트.",
        }
        with pytest.raises(ValidationError):
            ClaudeAnalysisOutput(**data)

    def test_empty_summary_raises_validation_error(self):
        """summary가 빈 문자열이면 ValidationError를 발생시켜야 한다"""
        from stock_picker.analysis.schema import ClaudeAnalysisOutput
        data = {
            "sentiment": "neutral",
            "sentiment_score": 0.0,
            "sector_tags": [],
            "keywords": ["테스트"],
            "summary": "",  # 빈 문자열 불허
        }
        with pytest.raises(ValidationError):
            ClaudeAnalysisOutput(**data)

    def test_missing_all_fields_raises_validation_error(self):
        """모든 필드 누락 시 ValidationError를 발생시켜야 한다"""
        from stock_picker.analysis.schema import ClaudeAnalysisOutput
        with pytest.raises(ValidationError):
            ClaudeAnalysisOutput()

    def test_summary_whitespace_only_raises_validation_error(self):
        """summary가 공백만 있으면 ValidationError를 발생시켜야 한다"""
        from stock_picker.analysis.schema import ClaudeAnalysisOutput
        data = {
            "sentiment": "neutral",
            "sentiment_score": 0.0,
            "sector_tags": [],
            "keywords": ["테스트"],
            "summary": "   ",  # 공백만 있는 문자열 불허
        }
        with pytest.raises(ValidationError):
            ClaudeAnalysisOutput(**data)
