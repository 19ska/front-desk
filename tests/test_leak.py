"""The reviewers' test, automated: sign in as a viewer and search every data response for identities."""
import csv

from tests.conftest import as_user

SAM, DANA = "sam.ferreira@brightline.example", "dana.whitfield@brightline.example"


def csv_rows():
    with open("data/visits.csv", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def identities():
    cols = ("visitor_name", "visitor_email", "visitor_company", "host_name", "host_email")
    return sorted({r[c].strip().lower() for r in csv_rows() for c in cols})


def all_list_pages():
    return [f"/api/visits?page={p}&page_size=200" for p in range(1, 11)]


def sample_ids():
    return [r["visit_id"] for r in csv_rows()][::25]


VIEWER_ENDPOINTS = (
    all_list_pages()
    + [f"/api/visits?type={t}" for t in ("guest", "interview", "contractor", "vendor")]
    + ["/api/visits?from=2026-08-01&to=2026-08-31", "/api/visit-types"]
    + [f"/api/visits/{i}" for i in sample_ids()]
    + ["/api/stats", "/api/stats?type=interview", "/api/stats?from=2026-08-01&to=2026-08-31"]
)


def fetch_all(client, headers, endpoints):
    bodies = []
    for url in endpoints:
        r = client.get(url, headers=headers)
        assert r.status_code in (200, 404), (url, r.status_code)
        bodies.append(r.text.lower())
    return bodies


def test_viewer_responses_contain_no_name_email_or_company(client):
    viewer = as_user(client, SAM)
    blob = "\n".join(fetch_all(client, viewer, VIEWER_ENDPOINTS))
    leaked = [needle for needle in identities() if needle in blob]
    assert leaked == []
    for key in ('"visitor"', '"host"', "visitor_name", "visitor_email", "host_name", "host_email", "company"):
        assert key not in blob, key


def test_the_same_sweep_as_admin_does_find_names(client):
    # Proves the sweep can see a leak: the admin's responses must contain identities.
    admin = as_user(client, DANA)
    blob = "\n".join(fetch_all(client, admin, VIEWER_ENDPOINTS[:1]))
    assert sum(needle in blob for needle in identities()) > 50


def test_viewer_cannot_read_the_user_list(client):
    r = client.get("/api/admin/users", headers=as_user(client, SAM))
    assert r.status_code == 403 and "dana" not in r.text.lower()
