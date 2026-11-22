from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.auth import (
    clear_session_cookie,
    create_token,
    get_current_user,
    hash_password,
    set_session_cookie,
    verify_password,
)
from app.config import get_settings
from app.db import get_db
from app.models import Contract, User, utcnow
from app.schemas import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class PasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class ProfileIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)


@router.get("/config")
def auth_config(db: Session = Depends(get_db)):
    """Public: tells the login page whether sign-up is open and if this is first-time setup."""
    has_users = bool(db.scalar(select(func.count()).select_from(User)))
    return {
        "allow_registration": get_settings().allow_registration or not has_users,
        "first_run": not has_users,
    }


@router.post("/register", response_model=UserOut, status_code=201)
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)):
    first_user = not db.scalar(select(func.count()).select_from(User))
    if not first_user and not get_settings().allow_registration:
        raise HTTPException(
            403, "Self-registration is disabled. Ask an administrator for an account."
        )
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    user = User(
        name=body.name.strip(),
        email=email,
        password_hash=hash_password(body.password),
        role="admin" if first_user else "user",
        last_login=utcnow(),
    )
    db.add(user)
    db.flush()
    if first_user:  # adopt contracts uploaded before accounts existed
        db.execute(update(Contract).where(Contract.owner_id.is_(None)).values(owner_id=user.id))
    db.commit()
    db.refresh(user)
    set_session_cookie(response, create_token(user))
    return user


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(403, "This account has been deactivated. Contact an administrator.")
    user.last_login = utcnow()
    db.commit()
    set_session_cookie(response, create_token(user))
    return user


@router.post("/logout", status_code=204)
def logout(response: Response):
    clear_session_cookie(response)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_profile(
    body: ProfileIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    user = db.merge(user)
    user.name = body.name.strip()
    db.commit()
    return user


@router.post("/password", status_code=204)
def change_password(
    body: PasswordIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    user = db.merge(user)
    user.password_hash = hash_password(body.new_password)
    db.commit()
