from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    db_host: str = "db"
    db_port: int = 5432
    db_name: str = "vpn_db"
    db_user: str = "postgres"
    db_password: str = "change_me_in_production"

    admin_username: str = "admin"
    admin_password: str = "change_me_in_production"
    environment: str = "dev"
    log_level: str = "INFO"
    library_log_level: str = "WARNING"

    happ_crypto_api_url: str = "https://crypto.happ.su/api-v2.php"
    subscription_base_url: str = "http://localhost:8000"

    @field_validator("log_level", "library_log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


settings = Settings()
