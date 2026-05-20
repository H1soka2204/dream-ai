import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = (BASE_DIR / "database" / "app.db").as_posix()


def database_uri():
    configured = os.getenv("DATABASE_URL")
    if not configured:
        return f"sqlite:///{DEFAULT_DB}"
    sqlite_prefix = "sqlite:///"
    if configured.startswith(sqlite_prefix):
        db_path = configured[len(sqlite_prefix) :]
        if db_path and db_path != ":memory:" and not Path(db_path).is_absolute():
            return f"sqlite:///{(BASE_DIR / db_path).as_posix()}"
    return configured


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")
    SQLALCHEMY_DATABASE_URI = database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AI_PROVIDER = os.getenv("AI_PROVIDER", "fallback").lower()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
