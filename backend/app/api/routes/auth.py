from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai.providers import configured_providers
from app.api.deps import get_current_user
from app.core.exceptions import AppError
from app.database.session import get_db
from app.models.models import User
from app.schemas.api import LoginIn, RegisterIn, SettingsIn, TokenOut, UserOut
from app.security.auth import create_access_token, hash_password, verify_password
from app.security.rate_limit import rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(u: User) -> UserOut:
    return UserOut(id=u.id, email=u.email, full_name=u.full_name, preferences=u.preferences or {})


@router.post("/register", response_model=TokenOut, status_code=201, dependencies=[Depends(rate_limit("auth", 10))])
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
        raise AppError("An account with this email already exists.", 409)
    user = User(email=email, full_name=body.full_name.strip(), password_hash=hash_password(body.password), preferences={})
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError("An account with this email already exists.", 409)
    return TokenOut(access_token=create_access_token(user.id), user=_user_out(user))


@router.post("/login", response_model=TokenOut, dependencies=[Depends(rate_limit("auth", 10))])
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == body.email.lower())).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.password_hash):
        raise AppError("Incorrect email or password.", 401)
    return TokenOut(access_token=create_access_token(user.id), user=_user_out(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return _user_out(user)


@router.get("/settings")
def get_settings_route(user: User = Depends(get_current_user)):
    prefs = user.preferences or {}
    return {"provider": prefs.get("provider"), "providers": configured_providers(), "user": _user_out(user)}


@router.put("/settings")
def update_settings(body: SettingsIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.provider and not configured_providers()[body.provider]:
        raise AppError(f"No API key is configured on the server for '{body.provider}'.", 400)
    prefs = dict(user.preferences or {})
    if body.provider:
        prefs["provider"] = body.provider
    user.preferences = prefs
    if body.full_name:
        user.full_name = body.full_name.strip()
    db.commit()
    return {"provider": prefs.get("provider"), "providers": configured_providers(), "user": _user_out(user)}
