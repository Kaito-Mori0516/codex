"""Read-only HTTP API Lambda backed by DynamoDB."""

from __future__ import annotations

import json
import logging
import os
from base64 import b64encode
from datetime import datetime, timezone
from typing import Any

from src.aws_database.dynamodb_repository import DynamoDataRepository
from src.data_catalog import DEFAULT_COUNTRIES, public_catalog
from src.exports import build_csv, build_xlsx
from src.services.aggregation_service import AggregationService


LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)
SORT_FIELDS = {
    "country": "country_name",
    "region": "region",
    "indicator": "indicator_name",
    "year": "year",
    "value": "value",
    "retrieved": "retrieved_at",
}
_repository: DynamoDataRepository | None = None


def _get_repository() -> DynamoDataRepository:
    global _repository
    if _repository is None:
        _repository = DynamoDataRepository(os.environ["DATA_TABLE_NAME"])
    return _repository


def _number(params: dict[str, str], name: str, kind: type[int] | type[float]) -> Any:
    value = params.get(name, "").strip()
    if not value:
        return None
    try:
        return kind(value)
    except (TypeError, ValueError):
        return None


def _filters(params: dict[str, str], default_indicator: str | None = None) -> dict[str, Any]:
    return {
        "search": params.get("search", "").strip()[:100],
        "country": params.get("country", "").strip().upper(),
        "region": params.get("region", "").strip(),
        "income_level": params.get("income_level", "").strip(),
        "indicator": params.get("indicator", default_indicator or "").strip(),
        "year_from": _number(params, "year_from", int),
        "year_to": _number(params, "year_to", int),
        "value_min": _number(params, "value_min", float),
        "value_max": _number(params, "value_max", float),
    }


def _response(status: int, payload: Any, *, cache_control: str = "public, max-age=300") -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {
            "content-type": "application/json; charset=utf-8",
            "cache-control": cache_control,
            "x-content-type-options": "nosniff",
        },
        "body": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    }


def _file_response(payload: bytes, content_type: str, filename: str) -> dict[str, Any]:
    return {
        "statusCode": 200,
        "isBase64Encoded": True,
        "headers": {
            "content-type": content_type,
            "content-disposition": f'attachment; filename="{filename}"',
            "cache-control": "private, no-store",
            "x-content-type-options": "nosniff",
        },
        "body": b64encode(payload).decode("ascii"),
    }


def _country_codes() -> tuple[str, ...]:
    configured = tuple(
        dict.fromkeys(
            code.strip().upper()
            for code in os.getenv("WORLD_BANK_COUNTRIES", "").split(",")
            if code.strip()
        )
    )
    return configured or DEFAULT_COUNTRIES


def handle_event(
    event: dict[str, Any], repository: DynamoDataRepository
) -> dict[str, Any]:
    context = event.get("requestContext", {}).get("http", {})
    method = context.get("method", "GET")
    path = context.get("path") or event.get("rawPath", "/")
    if path == "/api":
        path = "/"
    elif path.startswith("/api/"):
        path = path[4:]
    params = event.get("queryStringParameters") or {}
    if method != "GET":
        return _response(405, {"error": "Method not allowed"}, cache_control="no-store")

    if path == "/health":
        return _response(200, {"status": "ok", **repository.summary()}, cache_control="no-store")
    if path == "/summary":
        catalog = public_catalog(_country_codes())
        return _response(
            200,
            {
                **repository.summary(),
                "country_count": len(catalog["countries"]),
                "indicator_count": len(catalog["indicators"]),
                "source_name": "World Bank Indicators API",
            },
        )
    if path == "/catalog":
        return _response(200, public_catalog(_country_codes()), cache_control="public, max-age=3600")
    if path == "/countries":
        return _response(
            200,
            {"countries": public_catalog(_country_codes())["countries"]},
            cache_control="public, max-age=3600",
        )
    if path == "/indicators":
        return _response(
            200,
            {"indicators": public_catalog(_country_codes())["indicators"]},
            cache_control="public, max-age=3600",
        )
    default_indicator = os.getenv("DEFAULT_INDICATOR", "NY.GDP.MKTP.CD")
    if path == "/data":
        records = repository.all_records(
            _filters(params, default_indicator=default_indicator), limit=5000
        )
        sort_name = params.get("sort", "year")
        sort_field = SORT_FIELDS.get(sort_name, "year")
        descending = params.get("order", "desc").lower() != "asc"
        records.sort(key=lambda row: row.get(sort_field, ""), reverse=descending)
        page = max(1, int(_number(params, "page", int) or 1))
        page_size = min(100, max(10, int(_number(params, "page_size", int) or 25)))
        pages = max(1, (len(records) + page_size - 1) // page_size)
        page = min(page, pages)
        start = (page - 1) * page_size
        return _response(
            200,
            {
                "records": records[start : start + page_size],
                "total": len(records),
                "page": page,
                "page_size": page_size,
                "pages": pages,
            },
        )

    if path in {"/charts/timeseries", "/charts/ranking", "/charts/overview"}:
        chart = AggregationService(repository).chart_data(
            _filters(params, default_indicator=default_indicator)
        )
        if path == "/charts/timeseries":
            keys = ("indicator", "indicator_code", "unit", "latest_year", "time_series")
        elif path == "/charts/ranking":
            keys = ("indicator", "indicator_code", "unit", "latest_year", "ranking")
        else:
            keys = (
                "indicator",
                "indicator_code",
                "unit",
                "latest_year",
                "time_series",
                "region_comparison",
                "ranking",
            )
        return _response(200, {key: chart.get(key) for key in keys})

    if path in {"/export.csv", "/export.xlsx"}:
        filters = _filters(params, default_indicator=default_indicator)
        records = repository.all_records(filters, limit=20000)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        if path.endswith(".csv"):
            return _file_response(
                build_csv(records),
                "text/csv; charset=utf-8",
                f"world-data-lens-{timestamp}.csv",
            )
        return _file_response(
            build_xlsx(records, filters=filters),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            f"world-data-lens-{timestamp}.xlsx",
        )
    return _response(404, {"error": "Not found"}, cache_control="no-store")


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        return handle_event(event, _get_repository())
    except Exception:
        LOGGER.exception("Read API request failed")
        return _response(
            500,
            {"error": "The request could not be completed"},
            cache_control="no-store",
        )
