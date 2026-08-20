from __future__ import annotations

from pathlib import Path

import pytest

from src.config import Settings
from src.database.repository import DataRepository


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings.from_env(
        {
            "DATABASE_PATH": tmp_path / "test.db",
            "WORLD_BANK_COUNTRIES": "JPN,USA",
            "DATA_START_YEAR": 2020,
            "DATA_END_YEAR": 2021,
            "REQUEST_INTERVAL_SECONDS": 0,
            "INDICATORS": {
                "SP.POP.TOTL": {
                    "name": "Population, total",
                    "display_name": "人口（総数）",
                    "unit": "人",
                }
            },
        }
    )


@pytest.fixture
def repository(settings: Settings) -> DataRepository:
    repo = DataRepository(settings.database_path)
    repo.initialize()
    return repo


@pytest.fixture
def country_payload():
    return [
        {"page": 1, "pages": 1, "total": 2},
        [
            {
                "id": "JPN",
                "name": "Japan",
                "region": {"value": "East Asia & Pacific"},
                "incomeLevel": {"value": "High income"},
            },
            {
                "id": "USA",
                "name": "United States",
                "region": {"value": "North America"},
                "incomeLevel": {"value": "High income"},
            },
        ],
    ]


@pytest.fixture
def indicator_payload():
    return [
        {"page": 1, "pages": 1, "total": 5},
        [
            {"countryiso3code": "JPN", "date": "2021", "value": 125000000},
            {"countryiso3code": "JPN", "date": "2020", "value": 126000000},
            {"countryiso3code": "USA", "date": "2021", "value": 332000000},
            {"countryiso3code": "USA", "date": "2020", "value": 331000000},
            {"countryiso3code": "USA", "date": "2019", "value": None},
        ],
    ]


@pytest.fixture
def sample_records():
    base = {
        "region": "East Asia & Pacific",
        "income_level": "High income",
        "indicator_code": "SP.POP.TOTL",
        "indicator_name": "人口（総数）",
        "unit": "人",
        "period": "2020-01-01",
        "retrieved_at": "2026-08-20T00:00:00+00:00",
        "source_name": "World Bank Indicators API",
        "source_url": "https://api.worldbank.org/v2/example",
    }
    return [
        {**base, "country_code": "JPN", "country_name": "Japan", "value": 126.0, "year": 2020},
        {
            **base,
            "country_code": "JPN",
            "country_name": "Japan",
            "value": 125.0,
            "year": 2021,
            "period": "2021-01-01",
        },
        {
            **base,
            "country_code": "USA",
            "country_name": "United States",
            "region": "North America",
            "value": 331.0,
            "year": 2020,
        },
        {
            **base,
            "country_code": "USA",
            "country_name": "United States",
            "region": "North America",
            "value": 332.0,
            "year": 2021,
            "period": "2021-01-01",
        },
    ]
