from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment and `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Sound Trip API"
    debug: bool = False
    database_url: str = "sqlite:///./soundtrip.db"
    replicate_api_token: str = ""
    replicate_model: str = ""

    @property
    def sqlalchemy_database_url(self) -> str:
        """Sync driver URL for SQLAlchemy and Alembic (normalizes `sqlite+aiosqlite` from `.env`)."""
        url = self.database_url
        if url.startswith("sqlite+aiosqlite"):
            return url.replace("sqlite+aiosqlite", "sqlite", 1)
        return url


settings = Settings()
