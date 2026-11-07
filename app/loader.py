"""Turn the two raw CSV exports into clean Python objects.

Nothing here knows about the database. See docs/DATA_NOTES.md for why each
cleaning rule exists.
"""

import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal

Role = Literal["admin", "viewer"]
ROLE_RANK = {"viewer": 0, "admin": 1}

TIMESTAMP = "%Y-%m-%d %H:%M:%S"
# A second sign-in this soon after the first, with no sign-out, is the iPad
# recording the same tap twice (DATA_NOTES V1: real duplicates are 11-95 s apart).
DOUBLE_TAP_WINDOW = timedelta(seconds=120)


def normalise_email(raw: str) -> str:
    """Match emails the way a person would: ignore case and stray spaces."""
    return raw.strip().lower()


class DataFileError(ValueError):
    """A CSV the app can't trust. The message names the file, line and problem."""


def read_csv(path: Path, columns: set[str]) -> list[tuple[int, dict[str, str]]]:
    """Return (line number, row) pairs with every value stripped. Refuses malformed files."""
    # utf-8-sig drops a BOM if present; newline="" lets csv handle CRLF.
    #Each row becomes a dictionary where the column names are keys.
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        header = {h.strip() for h in reader.fieldnames or []}
        if missing := columns - header:
            raise DataFileError(f"{path.name}: missing column(s) {', '.join(sorted(missing))}")
        rows = []
        for row in reader:
            # DictReader files extra fields under None and fills short rows with None.
            if None in row or None in row.values():
                raise DataFileError(f"{path.name} line {reader.line_num}: expected {len(header)} fields")
            rows.append((reader.line_num, {k.strip(): v.strip() for k, v in row.items()}))
        return rows


@dataclass(frozen=True)
class AllowedUser:
    email: str
    name: str
    role: Role


def load_allowed_users(path: Path) -> list[AllowedUser]:
    users: dict[str, AllowedUser] = {}
    for line, row in read_csv(path, {"email", "name", "role"}):
        email = normalise_email(row["email"])
        if not email:
            print(f"Warning: skipping {path.name} line {line}: blank email")
            continue
        role = row["role"].lower()
        if role not in ROLE_RANK:
            print(f"Warning: skipping {email}: unknown role {row['role']!r} (no access)")
            continue
        existing = users.get(email)
        # Listed twice with different roles: grant the lower one.
        if existing and ROLE_RANK[existing.role] <= ROLE_RANK[role]:
            continue
        users[email] = AllowedUser(email, row["name"], role)
    return sorted(users.values(), key=lambda u: u.email)


@dataclass(frozen=True)
class Visit:
    visit_id: str
    visit_date: date
    signed_in_at: datetime
    signed_out_at: datetime | None
    visitor_name: str
    visitor_email: str
    visitor_company: str
    visit_type: str
    host_name: str
    host_email: str
    host_team: str
    pre_registered: bool

    @property
    def weekday(self) -> int:
        return self.signed_in_at.weekday()

    @property
    def hour(self) -> int:
        return self.signed_in_at.hour

    @property
    def duration_min(self) -> int | None:
        if self.signed_out_at is None:
            return None
        return round((self.signed_out_at - self.signed_in_at).total_seconds() / 60)


@dataclass(frozen=True)
class LoadedVisits:
    visits: list[Visit]
    dropped_duplicate_ids: list[str]
    missing_days: list[date]


def parse_visit(row: dict[str, str]) -> Visit:
    signed_in_at = datetime.strptime(row["signed_in_at"], TIMESTAMP)
    return Visit(
        visit_id=row["visit_id"],
        # The sign-in time is the source of truth for the date (they always agree in this export).
        visit_date=signed_in_at.date(),
        signed_in_at=signed_in_at,
        signed_out_at=datetime.strptime(row["signed_out_at"], TIMESTAMP) if row["signed_out_at"] else None,
        visitor_name=row["visitor_name"],
        visitor_email=normalise_email(row["visitor_email"]),
        visitor_company=row["visitor_company"],
        visit_type=row["visit_type"].lower(),
        host_name=row["host_name"],
        host_email=normalise_email(row["host_email"]),
        host_team=row["host_team"],
        pre_registered=row["pre_registered"].lower() == "true",
    )


def find_missing_weekdays(visits: list[Visit]) -> list[date]:
    """Mon-Fri days inside the data's range with no sign-ins at all: no data, not a quiet day."""
    if not visits:
        return []
    seen = {v.visit_date for v in visits}
    day, last = visits[0].visit_date, visits[-1].visit_date
    missing = []
    while day <= last:
        if day.weekday() < 5 and day not in seen:
            missing.append(day)
        day += timedelta(days=1)
    return missing


VISIT_COLUMNS = {
    "visit_id", "visit_date", "signed_in_at", "signed_out_at", "visitor_name", "visitor_email",
    "visitor_company", "visit_type", "host_name", "host_email", "host_team", "pre_registered",
}


def load_visits(path: Path) -> LoadedVisits:
    parsed = []
    for line, row in read_csv(path, VISIT_COLUMNS):
        try:
            parsed.append(parse_visit(row))
        except ValueError as e:
            # A visit we can't read would silently skew every count, so refuse the file.
            raise DataFileError(f"{path.name} line {line}: {e}") from e
    # Ids aren't in time order (the duplicates were appended), so sort by sign-in time.
    rows = sorted(parsed, key=lambda v: (v.signed_in_at, v.visit_id))
    kept: list[Visit] = []
    dropped: list[str] = []
    last_sign_in: dict[tuple[str, str, date], datetime] = {}
    for v in rows:
        key = (v.visitor_email, v.host_email, v.visit_date)
        previous = last_sign_in.get(key)
        if previous and v.signed_out_at is None and v.signed_in_at - previous <= DOUBLE_TAP_WINDOW:
            dropped.append(v.visit_id)
            continue
        last_sign_in[key] = v.signed_in_at
        kept.append(v)
    return LoadedVisits(kept, dropped, find_missing_weekdays(kept))
