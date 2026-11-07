"""Visits and stats. Every endpoint needs a session; what comes back depends on the role."""

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth import CurrentUser
from app.deps import current_user, get_conn
from app.filters import VisitFilters, parse_filters, parse_page, visit_types
from app.visits import compute_stats, get_visit, list_visits

router = APIRouter(prefix="/api")
PAGING = frozenset({"page", "page_size"})


@router.get("/visit-types")
def list_visit_types(user: CurrentUser = Depends(current_user), conn: sqlite3.Connection = Depends(get_conn)):
    return {"visit_types": visit_types(conn)}


def filters_json(f: VisitFilters) -> dict:
    return {
        "from": f.date_from.isoformat() if f.date_from else None,
        "to": f.date_to.isoformat() if f.date_to else None,
        "type": f.visit_type,
    }


@router.get("/visits")
def visits(request: Request, user: CurrentUser = Depends(current_user), conn: sqlite3.Connection = Depends(get_conn)):
    f = parse_filters(request.query_params, conn, PAGING)
    page, page_size = parse_page(request.query_params)
    # fetch role-appropriate visits
    result = list_visits(conn, f, page, page_size, identities=user.can_see_identities)
    if result["total"] and page > result["total_pages"]:
        raise HTTPException(400, f"Page {page} doesn't exist. There are {result['total_pages']} pages.")
    return {**result, "filters": filters_json(f)}


@router.get("/visits/{visit_id}")
def visit(visit_id: str, user: CurrentUser = Depends(current_user), conn: sqlite3.Connection = Depends(get_conn)):
    item = get_visit(conn, visit_id, identities=user.can_see_identities)
    if item is None:
        raise HTTPException(404, f"No visit with id {visit_id[:40]}.")
    return item


@router.get("/stats")
def stats(request: Request, user: CurrentUser = Depends(current_user), conn: sqlite3.Connection = Depends(get_conn)):
    # Aggregates only, so the same for both roles.
    return compute_stats(conn, parse_filters(request.query_params, conn))
