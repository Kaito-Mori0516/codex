"""Chart aggregation shared by SQLite/Flask and DynamoDB/Lambda."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Protocol


class ReadRepository(Protocol):
    def all_records(
        self, filters: dict[str, Any] | None = None, limit: int = 20000
    ) -> list[dict[str, Any]]: ...


def _empty_chart() -> dict[str, Any]:
    return {
        "indicator": None,
        "unit": None,
        "latest_year": None,
        "time_series": [],
        "region_comparison": [],
        "ranking": [],
    }


class AggregationService:
    def __init__(self, repository: ReadRepository) -> None:
        self.repository = repository

    def chart_data(self, filters: dict[str, Any]) -> dict[str, Any]:
        records = self.repository.all_records(filters)
        cleaned: list[dict[str, Any]] = []
        for record in records:
            try:
                value = float(record["value"])
                year = int(record["year"])
            except (KeyError, TypeError, ValueError):
                continue
            if not math.isfinite(value):
                continue
            cleaned.append({**record, "value": value, "year": year})

        if not cleaned:
            return _empty_chart()

        by_year: dict[int, list[float]] = defaultdict(list)
        for record in cleaned:
            by_year[record["year"]].append(record["value"])
        time_series = [
            {"year": year, "value": sum(values) / len(values)}
            for year, values in sorted(by_year.items())
        ]

        latest_year = max(by_year)
        latest = [record for record in cleaned if record["year"] == latest_year]
        by_region: dict[str, list[float]] = defaultdict(list)
        by_country: dict[tuple[str, str], float] = {}
        for record in latest:
            by_region[str(record["region"])].append(record["value"])
            country = (str(record["country_code"]), str(record["country_name"]))
            by_country[country] = max(record["value"], by_country.get(country, -math.inf))

        region_comparison = sorted(
            (
                {"region": region, "value": sum(values) / len(values)}
                for region, values in by_region.items()
            ),
            key=lambda row: row["value"],
            reverse=True,
        )
        ranking = [
            {"country_code": code, "country_name": name, "value": value}
            for (code, name), value in sorted(
                by_country.items(), key=lambda item: item[1], reverse=True
            )[:10]
        ]
        first = cleaned[0]
        return {
            "indicator": str(first["indicator_name"]),
            "indicator_code": str(first["indicator_code"]),
            "unit": str(first["unit"]),
            "latest_year": latest_year,
            "time_series": time_series,
            "region_comparison": region_comparison,
            "ranking": ranking,
        }
