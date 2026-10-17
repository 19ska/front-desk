from datetime import date
from pathlib import Path

import pytest

from app.loader import DataFileError, load_visits

REAL = Path("data/visits.csv")
HEADER = ("visit_id,visit_date,signed_in_at,signed_out_at,visitor_name,visitor_email,visitor_company,"
          "visit_type,host_name,host_email,host_team,pre_registered\n")


def row(vid, t_in, t_out="", email="a@co.example", host="h@b.example"):
    return f"{vid},{t_in[:10]},{t_in},{t_out},A B,{email},Co,guest,H H,{host},Sales,true\n"


def load(tmp_path, *rows):
    p = tmp_path / "v.csv"
    p.write_text(HEADER + "".join(rows))
    return load_visits(p)


def test_real_file_drops_exactly_the_58_duplicates():
    r = load_visits(REAL)
    assert len(r.visits) == 1953
    assert sorted(r.dropped_duplicate_ids) == [f"V{n:06d}" for n in range(1954, 2012)]


def test_real_file_missing_days_are_10_to_13_august():
    assert load_visits(REAL).missing_days == [date(2026, 8, d) for d in (10, 11, 12, 13)]


def test_derived_fields(tmp_path):
    v = load(tmp_path, row("V1", "2026-07-01 09:05:00", "2026-07-01 10:20:00")).visits[0]
    assert (v.weekday, v.hour, v.duration_min, v.pre_registered) == (2, 9, 75, True)


def test_blank_sign_out_is_none(tmp_path):
    assert load(tmp_path, row("V1", "2026-07-01 09:05:00")).visits[0].duration_min is None


def test_double_tap_within_120s_without_sign_out_is_dropped(tmp_path):
    r = load(tmp_path, row("V1", "2026-07-01 09:05:00", "2026-07-01 10:00:00"), row("V2", "2026-07-01 09:06:35"))
    assert r.dropped_duplicate_ids == ["V2"]


def test_near_duplicate_with_sign_out_is_kept(tmp_path):
    r = load(tmp_path, row("V1", "2026-07-01 09:05:00"), row("V2", "2026-07-01 09:05:30", "2026-07-01 10:00:00"))
    assert r.dropped_duplicate_ids == []


def test_same_day_return_visit_is_kept(tmp_path):
    r = load(tmp_path, row("V1", "2026-07-01 09:05:00"), row("V2", "2026-07-01 11:47:00"))
    assert len(r.visits) == 2


def test_different_host_is_not_a_duplicate(tmp_path):
    r = load(tmp_path, row("V1", "2026-07-01 09:05:00"), row("V2", "2026-07-01 09:05:20", host="x@b.example"))
    assert len(r.visits) == 2


def test_bad_timestamp_names_file_line_and_value(tmp_path):
    with pytest.raises(DataFileError, match=r"v\.csv line 3.*09\.05"):
        load(tmp_path, row("V1", "2026-07-01 09:05:00"), row("V2", "2026-07-01 09.05"))


def test_row_with_extra_field_names_file_and_line(tmp_path):
    with pytest.raises(DataFileError, match=r"v\.csv line 2"):
        load(tmp_path, row("V1", "2026-07-01 09:05:00").rstrip("\n") + ",extra\n")
