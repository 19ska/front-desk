import pytest

from tests.conftest import as_user

SAM, DANA = "sam.ferreira@brightline.example", "dana.whitfield@brightline.example"
VIEWER_KEYS = {"visit_id", "date", "signed_in", "signed_out", "duration_min", "visit_type", "host_team", "pre_registered"}


@pytest.fixture
def viewer(client):
    return as_user(client, SAM)


@pytest.fixture
def admin(client):
    return as_user(client, DANA)


def test_list_is_paged_newest_first(client, viewer):
    body = client.get("/api/visits", headers=viewer).json()
    assert (body["total"], body["page"], body["page_size"], body["total_pages"]) == (1953, 1, 50, 40)
    assert len(body["items"]) == 50
    assert body["items"][0]["signed_in"] >= body["items"][-1]["signed_in"]
    assert body["filters"] == {"from": None, "to": None, "type": None}


def test_viewer_items_have_exactly_the_viewer_fields(client, viewer):
    item = client.get("/api/visits", headers=viewer).json()["items"][0]
    assert set(item) == VIEWER_KEYS


def test_admin_items_add_visitor_and_host(client, admin):
    item = client.get("/api/visits/V001912", headers=admin).json()
    assert item["visitor"] == {"name": "Sofia Reyes", "email": "sreyes@oakfieldlega.example", "company": "Oakfield Legal"}
    assert item["host"] == {"name": "Nadia Ferreira", "email": "nadia.ferreira@brightline.example"}
    assert set(item) == VIEWER_KEYS | {"visitor", "host"}


def test_filters_are_inclusive_and_case_insensitive(client, viewer):
    body = client.get("/api/visits?from=2026-08-01&to=2026-08-31&type= Interview ", headers=viewer).json()
    assert body["total"] == 115
    assert body["filters"] == {"from": "2026-08-01", "to": "2026-08-31", "type": "interview"}
    assert client.get("/api/visits?from=2026-09-30&to=2026-09-30", headers=viewer).json()["total"] == 45  # 46 raw rows, one is a duplicate


def test_gap_days_return_an_honest_empty_200(client, viewer):
    body = client.get("/api/visits?from=2026-08-10&to=2026-08-13", headers=viewer).json()
    assert (body["total"], body["items"], body["total_pages"]) == (0, [], 0)


def test_page_past_the_end(client, viewer):
    r = client.get("/api/visits?page=999", headers=viewer)
    assert r.status_code == 400 and r.json() == {"error": "Page 999 doesn't exist. There are 40 pages."}


def test_single_visit_viewer_has_no_identity(client, viewer):
    item = client.get("/api/visits/V001912", headers=viewer).json()
    assert set(item) == VIEWER_KEYS and item["duration_min"] == 71


def test_unknown_and_deduplicated_ids_are_404_for_both_roles(client, viewer, admin):
    for headers in (viewer, admin):
        for vid in ("V001996", "nope"):
            r = client.get(f"/api/visits/{vid}", headers=headers)
            assert r.status_code == 404 and r.json() == {"error": f"No visit with id {vid}."}


def test_visits_need_a_session(client):
    assert client.get("/api/visits").status_code == 401
    assert client.get("/api/visits/V001912").status_code == 401
