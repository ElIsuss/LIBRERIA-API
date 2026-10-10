import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    database_url: str
    echo_sql: bool


settings = Settings(
    database_url=os.environ["DATABASE_URL"],
    echo_sql=os.getenv("ECHO_SQL", "false").strip().lower() in {"1", "true", "yes", "on"},
)