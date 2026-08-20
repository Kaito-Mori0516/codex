"""Pure transformation functions for World Bank API payloads."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TransformResult:
    records: list[dict[str, Any]]
    skipped_count: int
    failure_count: int


def parse_country_metadata(payload: list[Any], selected_codes: tuple[str, ...]) -> dict[str, dict[str, str]]:
    if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
        raise ValueError("Country metadata response structure changed")

    selected = set(selected_codes)
    countries: dict[str, dict[str, str]] = {}
    for item in payload[1]:
        if not isinstance(item, dict) or item.get("id") not in selected:
            continue
        region = item.get("region") or {}
        income = item.get("incomeLevel") or {}
        if region.get("value") == "Aggregates":
            continue
        countries[item["id"]] = {
            "country_name": str(item.get("name") or item["id"]).strip(),
            "region": str(region.get("value") or "Unknown").strip(),
            "income_level": str(income.get("value") or "Unknown").strip(),
        }

    missing = selected - countries.keys()
    if missing:
        raise ValueError(f"Country metadata missing for: {', '.join(sorted(missing))}")
    return countries


def parse_indicator_payload(
    payload: list[Any],
    countries: dict[str, dict[str, str]],
    indicator_code: str,
    indicator: dict[str, str],
    retrieved_at: str,
    source_url: str,
) -> TransformResult:
    if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
        raise ValueError("Indicator response structure changed")

    records: list[dict[str, Any]] = []
    skipped = 0
    failures = 0

    for item in payload[1]:
        if not isinstance(item, dict):
            failures += 1
            continue
        raw_value = item.get("value")
        if raw_value is None or raw_value == "":
            skipped += 1
            continue

        country_code = str(item.get("countryiso3code") or "").upper()
        metadata = countries.get(country_code)
        try:
            year = int(item.get("date"))
            value = float(raw_value)
            if metadata is None or not math.isfinite(value) or not 1900 <= year <= 2200:
                raise ValueError
        except (TypeError, ValueError):
            failures += 1
            continue

        records.append(
            {
                "country_code": country_code,
                "country_name": metadata["country_name"],
                "region": metadata["region"],
                "income_level": metadata["income_level"],
                "indicator_code": indicator_code,
                "indicator_name": indicator["display_name"],
                "unit": indicator["unit"],
                "value": value,
                "year": year,
                "period": f"{year}-01-01",
                "retrieved_at": retrieved_at,
                "source_name": "World Bank Indicators API",
                "source_url": source_url,
            }
        )

    return TransformResult(records=records, skipped_count=skipped, failure_count=failures)
