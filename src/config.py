from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_empty=True, extra="ignore"
    )

    database_url: str = "postgresql+asyncpg://vpn_user:vpn_pass@localhost:5432/vpn_db"
    admin_username: str = "admin"
    admin_password: str = "change_me_in_production"
    environment: str = "dev"


settings = Settings()
