# User ORM 모델 단위 테스트 (RED 단계)
import pytest
from sqlalchemy import inspect, UniqueConstraint

from stock_picker.db.models import User


class TestUserModel:
    """User 모델 컬럼 및 제약조건 검증"""

    def test_user_tablename(self):
        """테이블 이름이 'users'여야 한다"""
        assert User.__tablename__ == "users"

    def test_user_has_id_column(self):
        """id 컬럼이 존재하고 기본키여야 한다"""
        mapper = inspect(User)
        col = mapper.columns["id"]
        assert col.primary_key is True

    def test_user_has_username_column(self):
        """username 컬럼이 존재해야 한다"""
        mapper = inspect(User)
        assert "username" in mapper.columns

    def test_user_has_email_column(self):
        """email 컬럼이 존재해야 한다"""
        mapper = inspect(User)
        assert "email" in mapper.columns

    def test_user_has_hashed_password_column(self):
        """hashed_password 컬럼이 존재해야 한다"""
        mapper = inspect(User)
        assert "hashed_password" in mapper.columns

    def test_user_has_is_active_column(self):
        """is_active 컬럼이 존재하고 기본값이 True여야 한다"""
        mapper = inspect(User)
        col = mapper.columns["is_active"]
        assert col is not None
        # server_default 또는 default 중 하나로 True 설정
        assert col.default is not None or col.server_default is not None

    def test_user_has_created_at_column(self):
        """created_at 컬럼이 존재해야 한다"""
        mapper = inspect(User)
        assert "created_at" in mapper.columns

    def test_username_is_unique(self):
        """username 컬럼에 UNIQUE 제약조건이 있어야 한다"""
        mapper = inspect(User)
        col = mapper.columns["username"]
        assert col.unique is True

    def test_email_is_unique(self):
        """email 컬럼에 UNIQUE 제약조건이 있어야 한다"""
        mapper = inspect(User)
        col = mapper.columns["email"]
        assert col.unique is True

    def test_username_not_nullable(self):
        """username은 NULL 불가여야 한다"""
        mapper = inspect(User)
        assert mapper.columns["username"].nullable is False

    def test_email_not_nullable(self):
        """email은 NULL 불가여야 한다"""
        mapper = inspect(User)
        assert mapper.columns["email"].nullable is False

    def test_hashed_password_not_nullable(self):
        """hashed_password는 NULL 불가여야 한다"""
        mapper = inspect(User)
        assert mapper.columns["hashed_password"].nullable is False
