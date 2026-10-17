"""The Front Desk: one process serving the JSON API (and, from Phase 4, the pages)."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app import db
from app.errors import install_error_handlers
from app.loader import load_allowed_users, load_visits
from app.pages import install_pages
from app.routes import admin as admin_routes
from app.routes import auth as auth_routes
from app.routes import visits as visit_routes

DATA_DIR = Path("data")
DB_PATH = Path("var/frontdesk.db")
STATIC_DIR = Path("static")


def create_app(data_dir: Path = DATA_DIR, db_path: Path = DB_PATH, static_dir: Path = STATIC_DIR) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        conn = db.connect(db_path)
        try:
            db.init_schema(conn)
            users = load_allowed_users(data_dir / "allowed_users.csv")
            loaded = load_visits(data_dir / "visits.csv")
            db.replace_reference_data(conn, users, loaded)
        finally:
            conn.close()
        print_load_summary(users, loaded)
        yield

    app = FastAPI(title="The Front Desk", lifespan=lifespan)
    app.state.db_path = db_path
    install_error_handlers(app)
    app.include_router(auth_routes.router)
    app.include_router(visit_routes.router)
    app.include_router(admin_routes.router)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    # Last: the page catch-all must not shadow any API route.
    install_pages(app, static_dir)

    return app


def print_load_summary(users, loaded) -> None:
    admins = sum(u.role == "admin" for u in users)
    print(f"Loaded {len(users)} allowed users ({admins} admin, {len(users) - admins} viewer)")
    first, last = loaded.visits[0].visit_date, loaded.visits[-1].visit_date
    print(f"Loaded {len(loaded.visits)} visits from {first} to {last} "
          f"(dropped {len(loaded.dropped_duplicate_ids)} duplicate sign-ins)")
    if loaded.missing_days:
        print("No sign-ins recorded on: " + ", ".join(d.isoformat() for d in loaded.missing_days))


app = create_app()
