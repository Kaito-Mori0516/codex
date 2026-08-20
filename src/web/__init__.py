"""Flask application factory."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from flask import Flask, render_template

from src.config import Settings
from src.database.repository import DataRepository, DatabaseError
from src.web.routes import web


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    config = dict(test_config or {})
    settings = config.pop("SETTINGS", None) or Settings.from_env(config)
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
        static_url_path="/static",
    )
    app.config.update(TESTING=False, JSON_AS_ASCII=False)
    app.config.update(config)

    repository = DataRepository(settings.database_path)
    repository.initialize()
    app.extensions["settings"] = settings
    app.extensions["repository"] = repository
    app.register_blueprint(web)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    @app.template_filter("number")
    def format_number(value: Any) -> str:
        if value is None:
            return "—"
        number = float(value)
        if abs(number) >= 1_000_000_000:
            return f"{number / 1_000_000_000:.2f}B"
        if abs(number) >= 1_000_000:
            return f"{number / 1_000_000:.2f}M"
        if abs(number) >= 1_000:
            return f"{number:,.0f}"
        return f"{number:,.2f}".rstrip("0").rstrip(".")

    @app.template_filter("datetime")
    def format_datetime(value: str | None) -> str:
        if not value:
            return "未取得"
        try:
            parsed = datetime.fromisoformat(value)
            return parsed.strftime("%Y-%m-%d %H:%M UTC")
        except ValueError:
            return value

    @app.errorhandler(DatabaseError)
    def handle_database_error(error: DatabaseError):
        app.logger.exception("Database operation failed")
        return render_template(
            "error.html",
            title="データベースエラー",
            message="データベースを読み込めませんでした。設定とファイル権限を確認してください。",
        ), 500

    @app.errorhandler(404)
    def not_found(_error):
        return render_template(
            "error.html", title="ページが見つかりません", message="URLを確認してください。"
        ), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.exception("Unhandled application error", exc_info=error)
        return render_template(
            "error.html",
            title="処理エラー",
            message="処理を完了できませんでした。サーバーのログを確認してください。",
        ), 500

    return app
