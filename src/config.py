"""Environment-driven application settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.data_catalog import DEFAULT_COUNTRIES, INDICATORS

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # AWS Lambda package intentionally uses only runtime libraries.
    def load_dotenv(*_args: Any, **_kwargs: Any) -> bool:
        return False


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _as_bool(value: str | bool | None, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


@dataclass(frozen=True)
class Settings:
    database_path: Path
    api_base_url: str
    countries: tuple[str, ...]
    indicators: dict[str, dict[str, Any]]
    start_year: int
    end_year: int
    request_timeout: float
    max_retries: int
    backoff_factor: float
    request_interval: float
    user_agent: str
    flask_host: str
    flask_port: int
    flask_debug: bool

    @classmethod
    def from_env(cls, overrides: dict[str, Any] | None = None) -> "Settings":
        load_dotenv(PROJECT_ROOT / ".env")
        values: dict[str, Any] = dict(overrides or {})

        current_year = datetime.now(timezone.utc).year
        country_text = str(values.get("WORLD_BANK_COUNTRIES", os.getenv("WORLD_BANK_COUNTRIES", "")))
        countries = tuple(
            dict.fromkeys(code.strip().upper() for code in country_text.split(",") if code.strip())
        ) or DEFAULT_COUNTRIES

        database_value = values.get("DATABASE_PATH", os.getenv("DATABASE_PATH", "instance/dashboard.db"))
        end_year_text = values.get("DATA_END_YEAR", os.getenv("DATA_END_YEAR", ""))

        return cls(
            database_path=_resolve_path(database_value),
            api_base_url=str(
                values.get(
                    "WORLD_BANK_API_BASE_URL",
                    os.getenv("WORLD_BANK_API_BASE_URL", "https://api.worldbank.org/v2"),
                )
            ).rstrip("/"),
            countries=countries,
            indicators=values.get("INDICATORS", INDICATORS),
            start_year=int(values.get("DATA_START_YEAR", os.getenv("DATA_START_YEAR", "2010"))),
            end_year=int(end_year_text) if str(end_year_text).strip() else current_year,
            request_timeout=float(
                values.get("REQUEST_TIMEOUT_SECONDS", os.getenv("REQUEST_TIMEOUT_SECONDS", "20"))
            ),
            max_retries=int(values.get("REQUEST_MAX_RETRIES", os.getenv("REQUEST_MAX_RETRIES", "3"))),
            backoff_factor=float(
                values.get("REQUEST_BACKOFF_FACTOR", os.getenv("REQUEST_BACKOFF_FACTOR", "0.8"))
            ),
            request_interval=float(
                values.get("REQUEST_INTERVAL_SECONDS", os.getenv("REQUEST_INTERVAL_SECONDS", "0.5"))
            ),
            user_agent=str(
                values.get(
                    "USER_AGENT",
                    os.getenv("USER_AGENT", "OpenDataDashboard/1.0 (learning project)"),
                )
            ),
            flask_host=str(values.get("FLASK_HOST", os.getenv("FLASK_HOST", "127.0.0.1"))),
            flask_port=int(values.get("FLASK_PORT", os.getenv("FLASK_PORT", "5000"))),
            flask_debug=_as_bool(values.get("FLASK_DEBUG", os.getenv("FLASK_DEBUG"))),
        )
