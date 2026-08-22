"""Read-only HTTP API Lambda backed by DynamoDB."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from src.aws_database.dynamodb_repository import DynamoDataRepository
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


def _response(status: int, payload: Any) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json; charset=utf-8"},
        "body": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    }


def handle_event(
    event: dict[str, Any], repository: DynamoDataRepository
) -> dict[str, Any]:
    context = event.get("requestContext", {}).get("http", {})
    method = context.get("method", "GET")
    path = context.get("path") or event.get("rawPath", "/")
    params = event.get("queryStringParameters") or {}
    if method != "GET":
        return _response(405, {"error": "Method not allowed"})

    if path == "/health":
        return _response(200, {"status": "ok", **repository.summary()})
    if path == "/countries":
        return _response(200, {"countries": repository.filter_options()["countries"]})
    if path == "/indicators":
        return _response(200, {"indicators": repository.filter_options()["indicators"]})
    if path == "/data":
        records = repository.all_records(_filters(params), limit=5000)
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

    default_indicator = os.getenv("DEFAULT_INDICATOR", "SP.POP.TOTL")
    if path in {"/charts/timeseries", "/charts/ranking"}:
        chart = AggregationService(repository).chart_data(
            _filters(params, default_indicator=default_indicator)
        )
        if path == "/charts/timeseries":
            keys = ("indicator", "indicator_code", "unit", "latest_year", "time_series")
        else:
            keys = ("indicator", "indicator_code", "unit", "latest_year", "ranking")
        return _response(200, {key: chart.get(key) for key in keys})
    return _response(404, {"error": "Not found"})


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    try:
        return handle_event(event, _get_repository())
    except Exception:
        LOGGER.exception("Read API request failed")
        return _response(500, {"error": "The request could not be completed"})
