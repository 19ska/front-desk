import csv
import shutil
from pathlib import Path

from fastapi import Depends
from fastapi.testclient import TestClient

from app.deps import require_admin
from app.main import create_app
from tests.conftest import login, signup, extra_route

REFUSAL = "This email isn't on Brightline's access list. If you think it should be, ask Dana."
SAM = "sam.ferreira@brightline.example"
DANA = "dana.whitfield@brightline.example"


def allowed_emails():
    with open("data/allowed_users.csv", newline="", encoding="utf-8-sig") as f:
        return [r["email"] for r in csv.DictReader(f)]


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_every_listed_person_can_sign_up_exactly_as_written(client):
    for raw in allowed_emails():  # includes the messy ones, unmodified
        assert signup(client, raw).status_code == 201, raw


def test_stranger_is_refused_clearly(client):
    r = signup(client, "someone@brightline.example")
    assert r.status_code == 403 and r.json() == {"error": REFUSAL}


def test_messy_email_at_signup_and_login(client):
    assert signup(client, " Marcus.Vitale@BRIGHTLINE.example ").status_code == 201
    token = login(client, "marcus.vitale@brightline.example")
    assert client.get("/api/me", headers=bearer(token)).json()["role"] == "admin"


def test_signup_validation(client):
    assert signup(client, "  ").json() == {"error": "Enter your email address."}
    assert signup(client, SAM, password="short").json() == {"error": "Use a password of at least 8 characters."}
    assert signup(client, SAM).status_code == 201
    r = signup(client, SAM)
    assert r.status_code == 409 and r.json() == {"error": "An account already exists for this email. Sign in instead."}


def test_signup_with_missing_or_non_json_body_is_400(client):
    assert client.post("/api/auth/signup", json={}).status_code == 400
    assert client.post("/api/auth/signup", content=b"x", headers={"content-type": "application/json"}).status_code == 400


def test_login_failures_all_look_the_same(client):
    signup(client, SAM)
    bodies = [client.post("/api/auth/login", json={"email": e, "password": p})
              for e, p in [(SAM, "wrong pass"), ("x@y.example", "whatever1"), (DANA, "not signed up")]]
    assert {r.status_code for r in bodies} == {401}
    assert {r.json()["error"] for r in bodies} == {"Email or password is incorrect."}


def test_me_works_with_cookie_and_with_bearer(client):
    signup(client, SAM)
    token = login(client, SAM)  # TestClient keeps the cookie
    assert client.get("/api/me").json() == {"email": SAM, "name": "Sam Ferreira", "role": "viewer", "can_see_identities": False}
    client.cookies.clear()
    assert client.get("/api/me", headers=bearer(token)).status_code == 200


def test_login_cookie_flags(client):
    signup(client, SAM)
    r = client.post("/api/auth/login", json={"email": SAM, "password": "correct horse"})
    cookie = r.headers["set-cookie"].lower()
    assert "fd_session=" in cookie and "httponly" in cookie and "samesite=lax" in cookie and "max-age=28800" in cookie


def test_no_session_is_json_401(client):
    for headers in ({}, {"Authorization": "Bearer"}, {"Authorization": "Basic abc"}, {"Authorization": "Bearer nonsense"}):
        r = client.get("/api/me", headers=headers)
        assert r.status_code == 401 and r.json() == {"error": "Sign in to continue."}, headers


def test_logout_ends_the_session(client):
    signup(client, SAM)
    token = login(client, SAM)
    assert client.post("/api/auth/logout").status_code == 204
    client.cookies.clear()
    assert client.get("/api/me", headers=bearer(token)).status_code == 401


def test_require_admin(client):
    @extra_route(client.app, "/api/_admin_only")
    def admin_only(user=Depends(require_admin)):
        return {"ok": True}
    signup(client, SAM)
    signup(client, DANA)
    assert client.get("/api/_admin_only", headers=bearer(login(client, SAM))).json() == {"error": "You don't have access to this."}
    client.cookies.clear()
    assert client.get("/api/_admin_only", headers=bearer(login(client, DANA))).json() == {"ok": True}


def test_removed_from_list_then_restart_gets_401(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    shutil.copy("data/visits.csv", data)
    shutil.copy("data/allowed_users.csv", data)
    db_path = tmp_path / "t.db"
    with TestClient(create_app(data_dir=data, db_path=db_path)) as c:
        signup(c, SAM)
        token = login(c, SAM)
    lines = Path("data/allowed_users.csv").read_text().splitlines(keepends=True)
    (data / "allowed_users.csv").write_text("".join(l for l in lines if "sam.ferreira" not in l))
    with TestClient(create_app(data_dir=data, db_path=db_path)) as c:
        assert c.get("/api/me", headers=bearer(token)).status_code == 401


def test_empty_or_wrong_shape_body_says_what_to_send(client):
    for path in ("/api/auth/signup", "/api/auth/login"):
        for kwargs in ({}, {"json": []}, {"content": b"email=x", "headers": {"content-type": "application/x-www-form-urlencoded"}}):
            r = client.post(path, **kwargs)
            assert r.status_code == 400, (path, kwargs)
            assert r.json() == {"error": 'Send a JSON body like {"email": "...", "password": "..."}.'}, (path, kwargs)


def test_unencodable_text_is_400_not_500(client):
    lone_surrogate = '"\\ud800"'
    bodies = [
        ("/api/auth/signup", '{"email": "sam.ferreira@brightline.example", "password": "abcdefgh\\ud800"}'),
        ("/api/auth/signup", '{"email": ' + lone_surrogate + ', "password": "abcdefgh"}'),
        ("/api/auth/login", '{"email": ' + lone_surrogate + ', "password": "abcdefgh"}'),
    ]
    for path, raw in bodies:
        r = client.post(path, content=raw.encode(), headers={"content-type": "application/json"})
        assert r.status_code == 400, (path, raw, r.text)
        assert "valid text" in r.json()["error"]
