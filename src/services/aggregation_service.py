"""Pandas-based chart aggregation, independent from Flask and SQLite."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.database.repository import DataRepository


class AggregationService:
    def __init__(self, repository: DataRepository) -> None:
        self.repository = repository

    def chart_data(self, filters: dict[str, Any]) -> dict[str, Any]:
        records = self.repository.all_records(filters)
        if not records:
            return {
                "indicator": None,
                "unit": None,
                "latest_year": None,
                "time_series": [],
                "region_comparison": [],
                "ranking": [],
            }

        frame = pd.DataFrame.from_records(records)
        frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
        frame["year"] = pd.to_numeric(frame["year"], errors="coerce")
        frame = frame.dropna(subset=["value", "year"])
        if frame.empty:
            return {
                "indicator": None,
                "unit": None,
                "latest_year": None,
                "time_series": [],
                "region_comparison": [],
                "ranking": [],
            }

        time_series = (
            frame.groupby("year", as_index=False)["value"]
            .mean()
            .sort_values("year")
            .assign(year=lambda data: data["year"].astype(int))
        )
        latest_year = int(frame["year"].max())
        latest = frame[frame["year"] == latest_year]
        regions = (
            latest.groupby("region", as_index=False)["value"]
            .mean()
            .sort_values("value", ascending=False)
        )
        ranking = (
            latest.groupby(["country_code", "country_name"], as_index=False)["value"]
            .max()
            .sort_values("value", ascending=False)
            .head(10)
        )

        return {
            "indicator": str(frame.iloc[0]["indicator_name"]),
            "indicator_code": str(frame.iloc[0]["indicator_code"]),
            "unit": str(frame.iloc[0]["unit"]),
            "latest_year": latest_year,
            "time_series": [
                {"year": int(row.year), "value": float(row.value)}
                for row in time_series.itertuples(index=False)
            ],
            "region_comparison": [
                {"region": str(row.region), "value": float(row.value)}
                for row in regions.itertuples(index=False)
            ],
            "ranking": [
                {
                    "country_code": str(row.country_code),
                    "country_name": str(row.country_name),
                    "value": float(row.value),
                }
                for row in ranking.itertuples(index=False)
            ],
        }
