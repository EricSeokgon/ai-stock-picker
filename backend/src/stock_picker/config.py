# 환경변수 설정 - pydantic-settings 사용
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 환경변수 설정"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # 필수 설정 - 미설정 시 ValidationError 발생
    anthropic_api_key: str
    database_url: str

    # 선택 설정 - 기본값 있음
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"
