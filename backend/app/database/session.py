from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.database.engines import SessionLocal


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
