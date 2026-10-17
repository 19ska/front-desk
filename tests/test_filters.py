import pytest

from tests.conftest import as_user

SAM = "sam.ferreira@brightline.example"


@pytest.fixture
def viewer(client):
    return as_user(client, SAM)


def err(client, headers, query):
    r = client.get(f"/api/visits{query}", headers=headers)
    return r.status_code, r.json().get("error")


def test_visit_types_come_from_the_data(client, viewer):
    assert client.get("/api/visit-types", headers=viewer).json() == {"visit_types": ["contractor", "guest", "interview", "vendor"]}


def test_visit_types_needs_a_session(client):
    assert client.get("/api/visit-types").status_code == 401


def test_bad_dates(client, viewer):
    assert err(client, viewer, "?from=14/08/2026") == (400, "from must be a date written as YYYY-MM-DD.")
    assert err(client, viewer, "?to=2026-02-30") == (400, "to must be a date written as YYYY-MM-DD.")
    assert err(client, viewer, "?from=2026-08-31&to=2026-08-01") == (400, "The end date (2026-08-01) is before the start date (2026-08-31).")


def test_unknown_type_lists_the_real_ones(client, viewer):
    assert err(client, viewer, "?type=intervew") == (400, "Unknown visit type 'intervew'. Choose one of: contractor, guest, interview, vendor.")


def test_identity_shaped_params_are_refused(client, viewer):
    for q in ("?visitor_name=Felix", "?q=Felix", "?sort=visitor_name", "?visitor_email=x"):
        status, message = err(client, viewer, q)
        assert status == 400 and message.startswith("Unknown filter:"), q


def test_repeated_param_is_refused(client, viewer):
    assert err(client, viewer, "?type=guest&type=vendor") == (400, "Give type only once.")


def test_bad_paging(client, viewer):
    assert err(client, viewer, "?page=0") == (400, "page must be a whole number from 1.")
    assert err(client, viewer, "?page_size=500") == (400, "page_size must be a whole number from 1 to 200.")
    assert err(client, viewer, "?page=two") == (400, "page must be a whole number from 1.")


def test_huge_page_numbers_are_400_not_500(client, viewer):
    for q in ("?page=99999999999999999999", "?page=" + "9" * 5000, "?page_size=" + "9" * 5000):
        status, message = err(client, viewer, q)
        assert status == 400, q
