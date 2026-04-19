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

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


settings = Settings()
