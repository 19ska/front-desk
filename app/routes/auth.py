"""Sign-up, login, logout and "who am I"."""

import sqlite3
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, field_validator

from app.auth import SESSION_TTL, CurrentUser, create_session, delete_session, hash_password, verify_password
from app.deps import SESSION_COOKIE, current_user, get_conn, presented_token
from app.loader import normalise_email

router = APIRouter(prefix="/api")

MIN_PASSWORD = 8
# Friendly on purpose: the people refused here are mostly colleagues who mistyped (see docs/plan.md section 6).
NOT_ON_LIST = "This email isn't on Brightline's access list. If you think it should be, ask Dana."
BAD_LOGIN = "Email or password is incorrect."


class Credentials(BaseModel):
    email: str
    password: str

    @field_validator("email", "password")
    @classmethod
    def encodable(cls, value: str) -> str:
        # JSON allows lone surrogates (\ud800) that can't be hashed or stored: refuse them as bad input.
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            raise ValueError("must be valid text")
        return value


def user_json(email: str, name: str, role: str) -> dict:
    return {"email": email, "name": name, "role": role}


@router.post("/auth/signup", status_code=201)
def signup(body: Credentials, conn: sqlite3.Connection = Depends(get_conn)):
    email = normalise_email(body.email)
    if not email:
        raise HTTPException(400, "Enter your email address.")
    listed = conn.execute("SELECT name, role FROM allowed_users WHERE email = ?", (email,)).fetchone()
    if listed is None:
        raise HTTPException(403, NOT_ON_LIST)
    if len(body.password) < MIN_PASSWORD:
        raise HTTPException(400, f"Use a password of at least {MIN_PASSWORD} characters.")
    try:
        with conn:
            conn.execute("INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
                         (email, hash_password(body.password), datetime.now().isoformat()))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "An account already exists for this email. Sign in instead.")
    return user_json(email, listed["name"], listed["role"])


@router.post("/auth/login")
def login(body: Credentials, response: Response, conn: sqlite3.Connection = Depends(get_conn)):
    email = normalise_email(body.email)
    row = conn.execute(
        """SELECT u.password_hash, a.name, a.role FROM users u
           JOIN allowed_users a ON a.email = u.email WHERE u.email = ?""",
        (email,),
    ).fetchone()
    # Same answer for unknown email, not signed up and wrong password: a stranger learns nothing.
    if row is None or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(401, BAD_LOGIN)
    token = create_session(conn, email)
    response.set_cookie(SESSION_COOKIE, token, max_age=int(SESSION_TTL.total_seconds()),
                        httponly=True, samesite="lax", path="/")
    return {"token": token, "user": user_json(email, row["name"], row["role"])}


@router.post("/auth/logout", status_code=204)
def logout(request: Request, response: Response, user: CurrentUser = Depends(current_user),
           conn: sqlite3.Connection = Depends(get_conn)):
    delete_session(conn, presented_token(request))
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me")
def me(user: CurrentUser = Depends(current_user)):
    return {**user_json(user.email, user.name, user.role), "can_see_identities": user.can_see_identities}
