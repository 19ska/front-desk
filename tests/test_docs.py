import re
from pathlib import Path

from app.main import create_app

API_DOC = Path("docs/API.md")


def api_routes(tmp_path):
    # The OpenAPI schema lists every public route, including those from included routers.
    schema = create_app(db_path=tmp_path / "t.db").openapi()
    return {f"{method.upper()} {path}" for path, ops in schema["paths"].items() if path.startswith("/api/") for method in ops}


def test_every_api_route_is_documented(tmp_path):
    routes = api_routes(tmp_path)
    assert len(routes) >= 10  # guards against the route walk silently finding nothing
    doc = API_DOC.read_text()
    missing = [r for r in sorted(routes) if r.replace("{visit_id}", ":id") not in doc and r not in doc]
    assert missing == []


def test_readme_logins_match_the_account_script():
    readme = Path("README.md").read_text()
    script = Path("scripts/create_test_accounts.py").read_text()
    accounts = re.findall(r'\("([^"]+@[^"]+)", "([^"]+)", "(?:admin|viewer)"\)', script)
    assert len(accounts) == 2
    for email, password in accounts:
        assert email in readme and password in readme, email
