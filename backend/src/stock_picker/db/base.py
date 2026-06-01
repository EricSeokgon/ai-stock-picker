# SQLAlchemy 선언적 베이스
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """모든 ORM 모델의 기반 클래스"""
    pass
