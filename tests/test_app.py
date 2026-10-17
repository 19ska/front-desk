from fastapi.testclient import TestClient

from app import db
from app.main import create_app


def test_boots_loads_and_reports_health(tmp_path, capsys):
    app = create_app(db_path=tmp_path / "t.db")
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"status": "ok"}
        assert db.connect(tmp_path / "t.db").execute("SELECT COUNT(*) FROM visits").fetchone()[0] == 1953
    out = capsys.readouterr().out
    assert "1953 visits" in out and "58 duplicate" in out and "2026-08-10" in out
