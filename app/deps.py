"""FastAPI dependencies shared by the routes."""

import sqlite3
from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request

from app import db
from app.auth import CurrentUser, resolve_session

SESSION_COOKIE = "fd_session"


def get_conn(request: Request) -> Iterator[sqlite3.Connection]:
    # One connection per request: sharing one across FastAPI's worker threads isn't safe.
    conn = db.connect(request.app.state.db_path)
    try:
        yield conn
    finally:
        conn.close()


def presented_token(request: Request) -> str | None:
    """The session token from the browser's cookie, or from `Authorization: Bearer <token>` for curl."""
    if token := request.cookies.get(SESSION_COOKIE):
        return token
    parts = request.headers.get("authorization", "").split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def current_user(request: Request, conn: sqlite3.Connection = Depends(get_conn)) -> CurrentUser:
    token = presented_token(request)
    user = resolve_session(conn, token) if token else None
    if user is None:
        raise HTTPException(401, "Sign in to continue.")
    return user


def require_admin(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    # The real control: the API refuses, whatever the page shows.
    if user.role != "admin":
        raise HTTPException(403, "You don't have access to this.")
    return user
