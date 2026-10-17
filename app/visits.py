"""Visit queries. The role decides which columns are SELECTed in the first place.

A viewer's query never reads a name, email or company from the database, so
there is nothing to forget to remove from the response.
"""

import calendar
import sqlite3
from datetime import date
from statistics import median

from app.filters import VisitFilters, filters_sql

# Anything within 5% of the top value is reported as joint busiest rather than hidden.
TIE_SHARE = 0.95

VIEWER_COLUMNS = ("visit_id", "visit_date", "signed_in_at", "signed_out_at", "duration_min",
                  "visit_type", "host_team", "pre_registered")
ADMIN_COLUMNS = VIEWER_COLUMNS + ("visitor_name", "visitor_email", "visitor_company", "host_name", "host_email")


def columns_sql(identities: bool) -> str:
    return ", ".join(ADMIN_COLUMNS if identities else VIEWER_COLUMNS)


def row_to_item(row: sqlite3.Row, identities: bool) -> dict:
    item = {
        "visit_id": row["visit_id"],
        "date": row["visit_date"],
        "signed_in": row["signed_in_at"],
        "signed_out": row["signed_out_at"],
        "duration_min": row["duration_min"],
        "visit_type": row["visit_type"],
        "host_team": row["host_team"],
        "pre_registered": bool(row["pre_registered"]),
    }
    if identities:
        item["visitor"] = {"name": row["visitor_name"], "email": row["visitor_email"], "company": row["visitor_company"]}
        item["host"] = {"name": row["host_name"], "email": row["host_email"]}
    return item


def list_visits(conn: sqlite3.Connection, f: VisitFilters, page: int, page_size: int, identities: bool) -> dict:
    where, values = filters_sql(f)
    total = conn.execute(f"SELECT COUNT(*) FROM visits {where}", values).fetchone()[0]
    total_pages = -(-total // page_size)
    rows = conn.execute(
        f"SELECT {columns_sql(identities)} FROM visits {where} "
        "ORDER BY signed_in_at DESC, visit_id DESC LIMIT ? OFFSET ?",
        [*values, page_size, (page - 1) * page_size],
    ).fetchall()
    return {
        "items": [row_to_item(r, identities) for r in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }


def get_visit(conn: sqlite3.Connection, visit_id: str, identities: bool) -> dict | None:
    row = conn.execute(f"SELECT {columns_sql(identities)} FROM visits WHERE visit_id = ?", (visit_id,)).fetchone()
    return row_to_item(row, identities) if row else None


def busiest(values: dict, total: int) -> list:
    if not total:
        return []
    top = max(values.values())
    return [key for key, value in values.items() if value >= top * TIE_SHARE]


def clipped_range(conn: sqlite3.Connection, f: VisitFilters) -> tuple[date | None, date | None]:
    """The requested range trimmed to the dates the data actually covers."""
    first, last = conn.execute("SELECT MIN(visit_date), MAX(visit_date) FROM visits").fetchone()
    if first is None:
        return f.date_from, f.date_to
    first, last = date.fromisoformat(first), date.fromisoformat(last)
    lo, hi = max(f.date_from or first, first), min(f.date_to or last, last)
    if lo > hi:  # entirely outside the data: report exactly what was asked for
        return f.date_from, f.date_to
    return lo, hi


def compute_stats(conn: sqlite3.Connection, f: VisitFilters) -> dict:
    where, values = filters_sql(f)
    lo, hi = clipped_range(conn, f)
    span = (lo.isoformat() if lo else "", hi.isoformat() if hi else "")

    # Operating days: dates with any sign-in at all, whatever the type filter. A day with
    # no data (an outage, a weekend) isn't counted; a day with no vendors but other guests is.
    operating = [date.fromisoformat(r[0]) for r in conn.execute(
        "SELECT DISTINCT visit_date FROM visits WHERE visit_date BETWEEN ? AND ?", span)]
    days_per_weekday = {w: sum(d.weekday() == w for d in operating) for w in range(7)}

    by_weekday_count = dict(conn.execute(f"SELECT weekday, COUNT(*) FROM visits {where} GROUP BY weekday", values).fetchall())
    by_weekday = [
        {
            "weekday": w,
            "name": calendar.day_name[w],
            "visits": by_weekday_count.get(w, 0),
            "operating_days": days,
            "avg_per_day": round(by_weekday_count.get(w, 0) / days, 1),
        }
        for w, days in days_per_weekday.items() if days
    ]

    first_hour, last_hour = conn.execute("SELECT MIN(hour), MAX(hour) FROM visits").fetchone()
    by_hour_count = dict(conn.execute(f"SELECT hour, COUNT(*) FROM visits {where} GROUP BY hour", values).fetchall())
    hours = range(first_hour, last_hour + 1) if first_hour is not None else range(0)
    by_hour = [{"hour": h, "visits": by_hour_count.get(h, 0)} for h in hours]

    cell_count = {(w, h): n for w, h, n in conn.execute(
        f"SELECT weekday, hour, COUNT(*) FROM visits {where} GROUP BY weekday, hour", values)}
    by_weekday_hour = [
        {
            "weekday": d["weekday"],
            "hour": h["hour"],
            "visits": cell_count.get((d["weekday"], h["hour"]), 0),
            "avg_per_day": round(cell_count.get((d["weekday"], h["hour"]), 0) / d["operating_days"], 1),
        }
        for d in by_weekday for h in by_hour
    ]

    total = sum(by_hour_count.values())
    measured_where = f"{where} {'AND' if where else 'WHERE'} duration_min IS NOT NULL"
    durations = [r[0] for r in conn.execute(f"SELECT duration_min FROM visits {measured_where}", values)]

    return {
        "total_visits": total,
        "range": {"from": span[0] or None, "to": span[1] or None},
        "missing_days": [r[0] for r in conn.execute(
            "SELECT day FROM missing_days WHERE day BETWEEN ? AND ? ORDER BY day", span)],
        "by_weekday": by_weekday,
        "by_hour": by_hour,
        "by_weekday_hour": by_weekday_hour,
        "busiest_days": busiest({d["name"]: d["avg_per_day"] for d in by_weekday}, total),
        "busiest_hours": busiest({h["hour"]: h["visits"] for h in by_hour}, total),
        "visit_length": {
            "median_min": round(median(durations)) if durations else None,
            "measured_visits": len(durations),
            "total_visits": total,
        },
    }
