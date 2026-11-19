"""Two engines, two privilege levels.

* app_engine      -> `iq_app` role: application state in schema `app`.
* readonly_engine -> `iq_readonly` role: executes AI-generated SQL against schema `business`.
  Safety is enforced by the database itself (read-only transactions, statement timeout,
  restricted search_path) in addition to AST validation in security/sql_validator.py.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

_s = get_settings()

app_engine = create_engine(_s.app_database_url, pool_pre_ping=True, pool_size=5, max_overflow=5)

readonly_engine = create_engine(
    _s.readonly_database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    connect_args={
        "options": (
            f"-c statement_timeout={_s.query_timeout_seconds * 1000} "
            "-c default_transaction_read_only=on "
            "-c idle_in_transaction_session_timeout=10000 "
            "-c search_path=business"
        )
    },
)

SessionLocal = sessionmaker(bind=app_engine, expire_on_commit=False, autoflush=False)
