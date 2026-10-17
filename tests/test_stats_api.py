import pytest

from tests.conftest import as_user


@pytest.fixture
def viewer(client):
    return as_user(client, "sam.ferreira@brightline.example")


def stats(client, headers, query=""):
    r = client.get(f"/api/stats{query}", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_whole_dataset(client, viewer):
    s = stats(client, viewer)
    assert s["total_visits"] == 1953
    assert s["range"] == {"from": "2026-07-01", "to": "2026-09-30"}
    assert s["missing_days"] == ["2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13"]
    assert s["busiest_days"] == ["Tuesday", "Wednesday"]
    assert s["busiest_hours"] == [9]
    assert s["visit_length"] == {"median_min": 79, "measured_visits": 1083, "total_visits": 1953}


def test_weekday_averages_use_operating_days(client, viewer):
    by_day = {d["name"]: d for d in stats(client, viewer)["by_weekday"]}
    assert list(by_day) == ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    assert (by_day["Wednesday"]["visits"], by_day["Wednesday"]["operating_days"], by_day["Wednesday"]["avg_per_day"]) == (509, 13, 39.2)
    assert (by_day["Tuesday"]["operating_days"], by_day["Tuesday"]["avg_per_day"]) == (12, 39.6)


def test_hours_include_empty_lunch_hour(client, viewer):
    assert stats(client, viewer)["by_hour"] == [
        {"hour": 9, "visits": 726}, {"hour": 10, "visits": 252}, {"hour": 11, "visits": 270},
        {"hour": 12, "visits": 0}, {"hour": 13, "visits": 241}, {"hour": 14, "visits": 230}, {"hour": 15, "visits": 234}]


def test_type_filter_changes_the_answer(client, viewer):
    s = stats(client, viewer, "?type=guest")
    assert (s["total_visits"], s["busiest_days"], s["busiest_hours"]) == (798, ["Wednesday", "Thursday"], [10, 11])


def test_range_clipped_and_gap_reported(client, viewer):
    s = stats(client, viewer, "?from=2026-08-01&to=2026-08-31")
    assert s["range"] == {"from": "2026-08-01", "to": "2026-08-31"}
    assert s["missing_days"] == ["2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13"]
    assert s["total_visits"] == 494


def test_empty_selection_is_an_honest_200(client, viewer):
    for q in ("?from=2026-08-10&to=2026-08-13", "?from=2030-01-01&to=2030-12-31"):
        s = stats(client, viewer, q)
        assert (s["total_visits"], s["busiest_days"], s["busiest_hours"], s["visit_length"]["median_min"]) == (0, [], [], None), q


def test_stats_validate_like_visits(client, viewer):
    r = client.get("/api/stats?page=2", headers=viewer)
    assert r.status_code == 400 and r.json()["error"].startswith("Unknown filter: page")


def test_stats_need_a_session(client):
    assert client.get("/api/stats").status_code == 401


def test_one_sided_range_outside_the_data_is_not_inverted(client, viewer):
    assert stats(client, viewer, "?from=2030-01-01")["range"] == {"from": "2030-01-01", "to": None}
    assert stats(client, viewer, "?to=2020-01-01")["range"] == {"from": None, "to": "2020-01-01"}


def test_weekday_hour_grid(client, viewer):
    s = stats(client, viewer)
    grid = {(c["weekday"], c["hour"]): c for c in s["by_weekday_hour"]}
    assert len(grid) == 5 * 7
    assert sum(c["visits"] for c in s["by_weekday_hour"]) == 1953
    assert grid[(1, 9)]["avg_per_day"] == max(c["avg_per_day"] for c in s["by_weekday_hour"])  # Tuesday 9 am
    assert all(c["visits"] == 0 for c in s["by_weekday_hour"] if c["hour"] == 12)
