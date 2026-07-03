# AIAdvice 모델 단위 테스트 — SPEC-STOCK-014 M1
# RED 단계: 모델 정의·UNIQUE 제약·인덱스 검증
import pytest


class TestAIAdviceModelExists:
    """AIAdvice 모델이 존재하고 올바르게 정의되어야 한다"""

    def test_ai_advice_model_importable(self):
        """AIAdvice 모델을 import할 수 있어야 한다"""
        from stock_picker.db.models import AIAdvice
        assert AIAdvice is not None

    def test_ai_advice_table_name(self):
        """ai_advice 테이블명이 올바르게 설정되어야 한다"""
        from stock_picker.db.models import AIAdvice
        assert AIAdvice.__tablename__ == "ai_advice"


class TestAIAdviceColumns:
    """AIAdvice 모델 컬럼 정의 검증"""

    def test_required_columns_exist(self):
        """필수 컬럼이 모두 존재해야 한다"""
        from stock_picker.db.models import AIAdvice
        columns = {c.name for c in AIAdvice.__table__.columns}
        required = {"id", "user_id", "advice_type", "ref_date", "title", "created_at"}
        assert required.issubset(columns)

    def test_nullable_columns_exist(self):
        """nullable 컬럼이 존재해야 한다"""
        from stock_picker.db.models import AIAdvice
        columns = {c.name for c in AIAdvice.__table__.columns}
        nullable_cols = {"body", "payload", "risk_score", "feedback", "feedback_at"}
        assert nullable_cols.issubset(columns)

    def test_advice_type_max_length(self):
        """advice_type 컬럼은 String(20)이어야 한다"""
        from stock_picker.db.models import AIAdvice
        col = AIAdvice.__table__.columns["advice_type"]
        assert col.type.length == 20

    def test_title_max_length(self):
        """title 컬럼은 String(200)이어야 한다"""
        from stock_picker.db.models import AIAdvice
        col = AIAdvice.__table__.columns["title"]
        assert col.type.length == 200

    def test_feedback_max_length(self):
        """feedback 컬럼은 String(20)이어야 한다"""
        from stock_picker.db.models import AIAdvice
        col = AIAdvice.__table__.columns["feedback"]
        assert col.type.length == 20

    def test_user_id_not_nullable(self):
        """user_id 컬럼은 NOT NULL이어야 한다"""
        from stock_picker.db.models import AIAdvice
        col = AIAdvice.__table__.columns["user_id"]
        assert not col.nullable

    def test_advice_type_not_nullable(self):
        """advice_type 컬럼은 NOT NULL이어야 한다"""
        from stock_picker.db.models import AIAdvice
        col = AIAdvice.__table__.columns["advice_type"]
        assert not col.nullable

    def test_ref_date_not_nullable(self):
        """ref_date 컬럼은 NOT NULL이어야 한다"""
        from stock_picker.db.models import AIAdvice
        col = AIAdvice.__table__.columns["ref_date"]
        assert not col.nullable

    def test_title_not_nullable(self):
        """title 컬럼은 NOT NULL이어야 한다"""
        from stock_picker.db.models import AIAdvice
        col = AIAdvice.__table__.columns["title"]
        assert not col.nullable

    def test_body_nullable(self):
        """body 컬럼은 nullable이어야 한다"""
        from stock_picker.db.models import AIAdvice
        col = AIAdvice.__table__.columns["body"]
        assert col.nullable

    def test_risk_score_nullable(self):
        """risk_score 컬럼은 nullable이어야 한다"""
        from stock_picker.db.models import AIAdvice
        col = AIAdvice.__table__.columns["risk_score"]
        assert col.nullable

    def test_feedback_nullable(self):
        """feedback 컬럼은 nullable이어야 한다"""
        from stock_picker.db.models import AIAdvice
        col = AIAdvice.__table__.columns["feedback"]
        assert col.nullable

    def test_created_at_has_server_default(self):
        """created_at 컬럼은 server_default가 있어야 한다"""
        from stock_picker.db.models import AIAdvice
        col = AIAdvice.__table__.columns["created_at"]
        assert col.server_default is not None


class TestAIAdviceConstraints:
    """AIAdvice 테이블 제약조건 검증"""

    def test_unique_constraint_exists(self):
        """(user_id, advice_type, ref_date) UNIQUE 제약이 있어야 한다"""
        from stock_picker.db.models import AIAdvice
        from sqlalchemy import UniqueConstraint
        constraints = {
            c.name for c in AIAdvice.__table__.constraints
            if isinstance(c, UniqueConstraint)
        }
        assert "uq_ai_advice_user_type_date" in constraints

    def test_unique_constraint_covers_correct_columns(self):
        """UNIQUE 제약이 올바른 3개 컬럼을 포함해야 한다"""
        from stock_picker.db.models import AIAdvice
        from sqlalchemy import UniqueConstraint
        for c in AIAdvice.__table__.constraints:
            if isinstance(c, UniqueConstraint) and c.name == "uq_ai_advice_user_type_date":
                col_names = {col.name for col in c.columns}
                assert col_names == {"user_id", "advice_type", "ref_date"}
                return
        pytest.fail("uq_ai_advice_user_type_date 제약을 찾을 수 없습니다")

    def test_foreign_key_to_users(self):
        """user_id 컬럼이 users.id를 참조하는 FK가 있어야 한다"""
        from stock_picker.db.models import AIAdvice
        fk_targets = set()
        for col in AIAdvice.__table__.columns:
            for fk in col.foreign_keys:
                fk_targets.add(str(fk.target_fullname))
        assert "users.id" in fk_targets

    def test_index_exists(self):
        """(user_id, advice_type, created_at) 복합 인덱스가 있어야 한다"""
        from stock_picker.db.models import AIAdvice
        index_names = {idx.name for idx in AIAdvice.__table__.indexes}
        assert "ix_ai_advice_user_type" in index_names
