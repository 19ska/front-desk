def test_known_pages_serve_the_shell(client):
    for path in ("/login", "/signup", "/visits", "/visits?from=2026-08-01&type=interview", "/visits/V001912", "/admin/users"):
        r = client.get(path)
        assert r.status_code == 200 and '<main id="app"' in r.text, path


def test_root_redirects_to_visits(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/visits"


def test_unknown_page_is_a_real_404_with_the_shell(client):
    r = client.get("/no/such/page")
    assert r.status_code == 404 and '<main id="app"' in r.text


def test_api_404_is_still_json(client):
    assert client.get("/api/nope").json() == {"error": "No such endpoint: GET /api/nope"}


def test_static_files_are_served(client):
    assert client.get("/static/index.html").status_code == 200


def test_shell_needs_no_session_but_data_still_does(client):
    assert client.get("/admin/users").status_code == 200
    assert client.get("/api/admin/users").status_code == 401
