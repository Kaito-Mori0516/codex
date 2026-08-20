"""Beginner-friendly command line entry point."""

from __future__ import annotations

import argparse
import sys

from src.config import Settings
from src.database.repository import DataRepository, DatabaseError
from src.services.data_service import DataUpdateService
from src.web import create_app


def init_database(settings: Settings) -> int:
    repository = DataRepository(settings.database_path)
    repository.initialize()
    print(f"Database initialized: {settings.database_path}")
    return 0


def update_data(settings: Settings) -> int:
    repository = DataRepository(settings.database_path)
    repository.initialize()
    result = DataUpdateService(settings, repository).update()
    print(result.to_console_text())
    return 0 if result.status in {"success", "partial"} else 1


def run_server(settings: Settings, host: str | None, port: int | None, debug: bool | None) -> int:
    app = create_app({"SETTINGS": settings})
    app.run(
        host=host or settings.flask_host,
        port=port or settings.flask_port,
        debug=settings.flask_debug if debug is None else debug,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="World Bank Open Data Dashboard")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init-db", help="Create the SQLite database schema")
    subparsers.add_parser("update", help="Fetch, transform, and save current data")

    run_parser = subparsers.add_parser("run", help="Start the local web server")
    run_parser.add_argument("--host", help="Bind host, for example 127.0.0.1")
    run_parser.add_argument("--port", type=int, help="Bind port, for example 5000")
    run_parser.add_argument("--debug", action=argparse.BooleanOptionalAction, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    settings = Settings.from_env()
    try:
        if args.command == "init-db":
            return init_database(settings)
        if args.command == "update":
            return update_data(settings)
        return run_server(settings, args.host, args.port, args.debug)
    except DatabaseError as exc:
        print(f"Database error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
