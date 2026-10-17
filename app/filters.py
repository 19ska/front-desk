"""Query-string filters for visits and stats: validate them, then turn them into SQL.

Only the parameters named here are accepted. Anything else is refused, so there is
no way to filter, search or sort by a visitor's identity.
"""

import re
import sqlite3
from dataclasses import dataclass
from datetime import date

from fastapi import HTTPException
from starlette.datastructures import QueryParams

FILTERS = ("from", "to", "type")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


@dataclass(frozen=True)
class VisitFilters:
    date_from: date | None = None
    date_to: date | None = None
    visit_type: str | None = None


def bad(message: str) -> HTTPException:
    return HTTPException(400, message)


def visit_types(conn: sqlite3.Connection) -> list[str]:
    return [r[0] for r in conn.execute("SELECT DISTINCT visit_type FROM visits ORDER BY visit_type")]


def single(params: QueryParams, name: str) -> str | None:
    values = params.getlist(name)
    if len(values) > 1:
        raise bad(f"Give {name} only once.")
    return values[0] if values else None


def parse_date(params: QueryParams, name: str) -> date | None:
    raw = single(params, name)
    if raw is None or raw.strip() == "":
        return None
    raw = raw.strip()
    try:
        if not ISO_DATE.match(raw):
            raise ValueError
        return date.fromisoformat(raw)
    except ValueError:
        raise bad(f"{name} must be a date written as YYYY-MM-DD.")


def parse_filters(params: QueryParams, conn: sqlite3.Connection, extra: frozenset[str] = frozenset()) -> VisitFilters:
    accepted = FILTERS + tuple(sorted(extra))
    for name in params.keys():
        if name not in accepted:
            raise bad(f"Unknown filter: {name[:40]}. Use {', '.join(accepted)}.")
    date_from, date_to = parse_date(params, "from"), parse_date(params, "to")
    if date_from and date_to and date_to < date_from:
        raise bad(f"The end date ({date_to}) is before the start date ({date_from}).")
    visit_type = (single(params, "type") or "").strip().lower() or None
    if visit_type is not None:
        known = visit_types(conn)
        if visit_type not in known:
            raise bad(f"Unknown visit type '{visit_type[:40]}'. Choose one of: {', '.join(known)}.")
    return VisitFilters(date_from, date_to, visit_type)


def parse_whole_number(params: QueryParams, name: str, default: int, maximum: int | None) -> int:
    raw = single(params, name)
    if raw is None:
        return default
    digits = raw.strip()
    # Capped at 9 digits: anything longer is nonsense and would overflow SQLite's OFFSET.
    value = int(digits) if digits.isascii() and digits.isdigit() and len(digits) <= 9 else 0
    if value < 1 or (maximum and value > maximum):
        limit = f"from 1 to {maximum}" if maximum else "from 1"
        raise bad(f"{name} must be a whole number {limit}.")
    return value


def parse_page(params: QueryParams) -> tuple[int, int]:
    return (parse_whole_number(params, "page", 1, None),
            parse_whole_number(params, "page_size", DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE))


def filters_sql(f: VisitFilters) -> tuple[str, list]:
    clauses, values = [], []
    if f.date_from:
        clauses.append("visit_date >= ?")
        values.append(f.date_from.isoformat())
    if f.date_to:
        # Inclusive: "to 30 Sep" includes visits on 30 Sep.
        clauses.append("visit_date <= ?")
        values.append(f.date_to.isoformat())
    if f.visit_type:
        clauses.append("visit_type = ?")
        values.append(f.visit_type)
    return ("WHERE " + " AND ".join(clauses) if clauses else ""), values
