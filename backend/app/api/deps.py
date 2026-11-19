from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.database.session import get_db
from app.models.models import User
from app.security.auth import decode_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> User:
    if creds is None:
        raise AppError("Not authenticated", 401)
    user = db.get(User, decode_token(creds.credentials))
    if user is None:
        raise AppError("User no longer exists", 401)
    return user
