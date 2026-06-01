# 환경변수 설정 테스트 - 설정 로딩 및 유효성 검증
import os
import pytest
from unittest.mock import patch
from pydantic import ValidationError

from stock_picker.config import Settings


class TestSettings:
    """설정 로딩 및 유효성 검증 테스트"""

    def test_loads_from_env_vars(self):
        """환경변수에서 설정을 정상적으로 로드해야 한다"""
        env_vars = {
            "ANTHROPIC_API_KEY": "test-api-key",
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/db",
            "REDIS_URL": "redis://localhost:6379/0",
            "LOG_LEVEL": "DEBUG",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            assert settings.anthropic_api_key == "test-api-key"
            assert settings.database_url == "postgresql+asyncpg://user:pass@localhost:5432/db"
            assert settings.redis_url == "redis://localhost:6379/0"
            assert settings.log_level == "DEBUG"

    def test_redis_url_has_default_value(self):
        """REDIS_URL이 없으면 기본값을 사용해야 한다"""
        env_vars = {
            "ANTHROPIC_API_KEY": "test-api-key",
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/db",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            assert settings.redis_url == "redis://localhost:6379/0"

    def test_log_level_has_default_value(self):
        """LOG_LEVEL이 없으면 기본값 INFO를 사용해야 한다"""
        env_vars = {
            "ANTHROPIC_API_KEY": "test-api-key",
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/db",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            assert settings.log_level == "INFO"

    def test_raises_validation_error_when_anthropic_api_key_missing(self):
        """ANTHROPIC_API_KEY가 없으면 ValidationError를 발생시켜야 한다"""
        env_vars = {
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost:5432/db",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValidationError):
                Settings()

    def test_raises_validation_error_when_database_url_missing(self):
        """DATABASE_URL이 없으면 ValidationError를 발생시켜야 한다"""
        env_vars = {
            "ANTHROPIC_API_KEY": "test-api-key",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValidationError):
                Settings()

    def test_raises_validation_error_when_all_required_vars_missing(self):
        """필수 환경변수가 모두 없으면 ValidationError를 발생시켜야 한다"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError):
                Settings()
