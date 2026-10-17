from fastapi import Body
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import extra_route


def test_unknown_api_path_is_json_404(client):
    r = client.get("/api/nope")
    assert r.status_code == 404
    assert r.json() == {"error": "No such endpoint: GET /api/nope"}


def test_validation_error_is_400_with_readable_message(client):
    @extra_route(client.app, "/api/_echo", ["POST"])
    def echo(n: int = Body(embed=True)):
        return {"n": n}
    r = client.post("/api/_echo", json={})
    assert r.status_code == 400
    assert "n" in r.json()["error"]


def test_non_json_body_is_400(client):
    @extra_route(client.app, "/api/_echo2", ["POST"])
    def echo2(n: int = Body(embed=True)):
        return {"n": n}
    r = client.post("/api/_echo2", content=b"not json", headers={"content-type": "application/json"})
    assert r.status_code == 400 and "error" in r.json()


def test_unexpected_exception_is_json_500(tmp_path):
    app = create_app(db_path=tmp_path / "t.db")

    @extra_route(app, "/api/_boom")
    def boom():
        raise RuntimeError("secret detail")
    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/api/_boom")
    assert r.status_code == 500
    assert r.json() == {"error": "Something went wrong on our side. Try again."}
