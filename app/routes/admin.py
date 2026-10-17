"""Admin-only endpoints. require_admin is the real control; hiding the page link is just a courtesy."""

import sqlite3

from fastapi import APIRouter, Depends

from app.auth import CurrentUser
from app.deps import get_conn, require_admin

router = APIRouter(prefix="/api/admin")


@router.get("/users")
def users(user: CurrentUser = Depends(require_admin), conn: sqlite3.Connection = Depends(get_conn)):
    rows = conn.execute(
        """SELECT a.email, a.name, a.role, u.email IS NOT NULL AS signed_up
           FROM allowed_users a LEFT JOIN users u ON u.email = a.email
           ORDER BY a.role = 'admin' DESC, a.name"""
    ).fetchall()
    return {"users": [{"email": r["email"], "name": r["name"], "role": r["role"], "signed_up": bool(r["signed_up"])}
                      for r in rows]}
