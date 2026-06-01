# ORM 모델 정의 테스트 - 테이블, 컬럼, 제약조건 검증
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY


class TestModelDefinitions:
    """SQLAlchemy ORM 모델 정의 검증 테스트"""

    def test_article_model_exists(self):
        """Article 모델이 정의되어 있어야 한다"""
        from stock_picker.db.models import Article
        assert Article is not None

    def test_analysis_result_model_exists(self):
        """AnalysisResult 모델이 정의되어 있어야 한다"""
        from stock_picker.db.models import AnalysisResult
        assert AnalysisResult is not None

    def test_stock_mention_model_exists(self):
        """StockMention 모델이 정의되어 있어야 한다"""
        from stock_picker.db.models import StockMention
        assert StockMention is not None

    def test_sector_trend_model_exists(self):
        """SectorTrend 모델이 정의되어 있어야 한다"""
        from stock_picker.db.models import SectorTrend
        assert SectorTrend is not None

    def test_recommendation_model_exists(self):
        """Recommendation 모델이 정의되어 있어야 한다"""
        from stock_picker.db.models import Recommendation
        assert Recommendation is not None


class TestArticleModel:
    """Article 모델 컬럼 및 제약조건 테스트"""

    def test_article_table_name(self):
        """Articles 테이블명이 올바르게 설정되어야 한다"""
        from stock_picker.db.models import Article
        assert Article.__tablename__ == "articles"

    def test_article_has_required_columns(self):
        """Article 모델이 필수 컬럼을 모두 가져야 한다"""
        from stock_picker.db.models import Article
        columns = {c.name for c in Article.__table__.columns}
        assert "id" in columns
        assert "url" in columns
        assert "source" in columns
        assert "title" in columns
        assert "content" in columns
        assert "published_at" in columns
        assert "collected_at" in columns
        assert "status" in columns

    def test_article_url_has_unique_constraint(self):
        """url 컬럼은 UNIQUE 제약조건을 가져야 한다"""
        from stock_picker.db.models import Article
        url_col = Article.__table__.columns["url"]
        assert url_col.unique is True

    def test_article_status_has_default(self):
        """status 컬럼은 기본값 'collected'를 가져야 한다"""
        from stock_picker.db.models import Article
        status_col = Article.__table__.columns["status"]
        # 서버 기본값 또는 Python 기본값 확인
        assert (
            str(status_col.default.arg) == "collected"
            or (status_col.server_default is not None and "collected" in str(status_col.server_default.arg))
        )


class TestAnalysisResultModel:
    """AnalysisResult 모델 테스트"""

    def test_analysis_result_table_name(self):
        """analysis_results 테이블명이 올바르게 설정되어야 한다"""
        from stock_picker.db.models import AnalysisResult
        assert AnalysisResult.__tablename__ == "analysis_results"

    def test_analysis_result_has_required_columns(self):
        """AnalysisResult 모델이 필수 컬럼을 모두 가져야 한다"""
        from stock_picker.db.models import AnalysisResult
        columns = {c.name for c in AnalysisResult.__table__.columns}
        assert "id" in columns
        assert "article_id" in columns
        assert "sentiment" in columns
        assert "sentiment_score" in columns
        assert "sector_tags" in columns
        assert "keywords" in columns
        assert "summary" in columns
        assert "tokens_used" in columns
        assert "analyzed_at" in columns

    def test_analysis_result_sector_tags_is_array(self):
        """sector_tags 컬럼은 TEXT 배열(ARRAY(String)) 타입이어야 한다"""
        from stock_picker.db.models import AnalysisResult
        sector_tags_col = AnalysisResult.__table__.columns["sector_tags"]
        # ARRAY(String) 타입 확인
        assert isinstance(sector_tags_col.type, ARRAY)
        assert isinstance(sector_tags_col.type.item_type, String)

    def test_analysis_result_keywords_is_array(self):
        """keywords 컬럼은 TEXT 배열(ARRAY(String)) 타입이어야 한다"""
        from stock_picker.db.models import AnalysisResult
        keywords_col = AnalysisResult.__table__.columns["keywords"]
        assert isinstance(keywords_col.type, ARRAY)

    def test_analysis_result_has_article_foreign_key(self):
        """article_id는 articles 테이블을 참조하는 외래키여야 한다"""
        from stock_picker.db.models import AnalysisResult
        article_id_col = AnalysisResult.__table__.columns["article_id"]
        fks = list(article_id_col.foreign_keys)
        assert len(fks) == 1
        assert "articles" in str(fks[0].target_fullname)


class TestStockMentionModel:
    """StockMention 모델 테스트"""

    def test_stock_mention_table_name(self):
        """stock_mentions 테이블명이 올바르게 설정되어야 한다"""
        from stock_picker.db.models import StockMention
        assert StockMention.__tablename__ == "stock_mentions"

    def test_stock_mention_has_required_columns(self):
        """StockMention 모델이 필수 컬럼을 모두 가져야 한다"""
        from stock_picker.db.models import StockMention
        columns = {c.name for c in StockMention.__table__.columns}
        assert "id" in columns
        assert "article_id" in columns
        assert "stock_name" in columns
        assert "krx_code" in columns
        assert "mention_status" in columns

    def test_krx_code_is_nullable(self):
        """krx_code 컬럼은 nullable이어야 한다"""
        from stock_picker.db.models import StockMention
        krx_code_col = StockMention.__table__.columns["krx_code"]
        assert krx_code_col.nullable is True


class TestSectorTrendModel:
    """SectorTrend 모델 테스트"""

    def test_sector_trend_table_name(self):
        """sector_trends 테이블명이 올바르게 설정되어야 한다"""
        from stock_picker.db.models import SectorTrend
        assert SectorTrend.__tablename__ == "sector_trends"

    def test_sector_trend_has_required_columns(self):
        """SectorTrend 모델이 필수 컬럼을 모두 가져야 한다"""
        from stock_picker.db.models import SectorTrend
        columns = {c.name for c in SectorTrend.__table__.columns}
        assert "id" in columns
        assert "sector" in columns
        assert "trade_date" in columns
        assert "news_volume" in columns
        assert "avg_sentiment" in columns
        assert "trend_score" in columns
        assert "computed_at" in columns


class TestRecommendationModel:
    """Recommendation 모델 테스트"""

    def test_recommendation_table_name(self):
        """recommendations 테이블명이 올바르게 설정되어야 한다"""
        from stock_picker.db.models import Recommendation
        assert Recommendation.__tablename__ == "recommendations"

    def test_recommendation_has_required_columns(self):
        """Recommendation 모델이 필수 컬럼을 모두 가져야 한다"""
        from stock_picker.db.models import Recommendation
        columns = {c.name for c in Recommendation.__table__.columns}
        assert "id" in columns
        assert "trade_date" in columns
        assert "asset_type" in columns
        assert "krx_code" in columns
        assert "rank" in columns
        assert "total_score" in columns
        assert "sentiment_score" in columns
        assert "volume_score" in columns
        assert "momentum_score" in columns
        assert "anomaly_score" in columns
        assert "reasoning" in columns
        assert "computed_at" in columns

    def test_recommendation_has_composite_index(self):
        """recommendations 테이블은 (trade_date, asset_type, rank) 복합 인덱스를 가져야 한다"""
        from stock_picker.db.models import Recommendation
        indexes = list(Recommendation.__table__.indexes)
        # 복합 인덱스 존재 여부 확인
        composite_index_found = False
        for idx in indexes:
            col_names = {c.name for c in idx.columns}
            if "trade_date" in col_names and "asset_type" in col_names and "rank" in col_names:
                composite_index_found = True
                break
        assert composite_index_found, "recommendations 테이블에 (trade_date, asset_type, rank) 복합 인덱스가 없음"
