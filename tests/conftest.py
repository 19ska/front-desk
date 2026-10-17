import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(db_path=tmp_path / "t.db")) as c:
        yield c


def signup(client, email, password="correct horse"):
    return client.post("/api/auth/signup", json={"email": email, "password": password})


def login(client, email, password="correct horse"):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def as_user(client, email, password="correct horse"):
    """Sign up (if needed) and log in; return Bearer headers.

    Clears the client's cookies, because a stale cookie would otherwise win over the Bearer header.
    """
    r = signup(client, email, password)
    assert r.status_code in (201, 409), r.text
    token = login(client, email, password)
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}


def extra_route(app, path, methods=("GET",)):
    """Decorator for test-only endpoints. Puts them before the page catch-all, which would otherwise shadow them."""
    def register(endpoint):
        app.add_api_route(path, endpoint, methods=list(methods))
        app.router.routes.insert(0, app.router.routes.pop())
        return endpoint
    return register
