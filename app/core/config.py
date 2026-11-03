from pathlib import Path

from pydantic import AliasChoices, Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",
    )

    postgres_user: str | None = None
    postgres_password: str | None = None
    postgres_db: str | None = None
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    jwt_secret_key: str | None = None
    jwt_algorithm: str = "HS256"
    jwt_expire_seconds: int = 3600
    cookie_secure: bool = False

    bcrypt_rounds: int = 12
    bcrypt_max_concurrency: int = 4
    db_pool_size: int = 5
    sql_echo: bool = Field(
        default=False,
        validation_alias=AliasChoices("SQL_ECHO", "ECHO_SQL", "sql_echo"),
    )
    legacy_database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
    )

    @model_validator(mode="after")
    def validate_settings(self):
        if self.legacy_database_url:
            return self

        missing = []
        for field_name in ("postgres_user", "postgres_password", "postgres_db"):
            if getattr(self, field_name) in (None, ""):
                missing.append(field_name)

        if self.jwt_secret_key in (None, ""):
            missing.append("jwt_secret_key")

        if missing:
            raise ValueError(
                "Missing required settings: " + ", ".join(missing) + ". "
                "Use POSTGRES_* and JWT_SECRET_KEY, or provide DATABASE_URL for legacy compatibility."
            )

        return self

    @computed_field
    @property
    def database_url(self) -> str:
        if self.legacy_database_url:
            return self.legacy_database_url

        if self.postgres_user is None or self.postgres_password is None or self.postgres_db is None:
            raise ValueError("database_url cannot be built without POSTGRES_USER, POSTGRES_PASSWORD and POSTGRES_DB")

        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()