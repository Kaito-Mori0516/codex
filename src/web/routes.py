"""Read-only web and JSON routes."""

from __future__ import annotations

import csv
from io import StringIO
from typing import Any

from flask import Blueprint, Response, current_app, jsonify, render_template, request, url_for

from src.config import INDICATORS
from src.database.repository import DataRepository, SORT_COLUMNS
from src.services.aggregation_service import AggregationService


web = Blueprint("web", __name__)


def repository() -> DataRepository:
    return current_app.extensions["repository"]


def parse_number(name: str, number_type: type[int] | type[float]) -> int | float | None:
    value = request.args.get(name, "").strip()
    if not value:
        return None
    try:
        return number_type(value)
    except (TypeError, ValueError):
        return None


def parse_filters(default_indicator: str | None = None) -> dict[str, Any]:
    indicator = request.args.get("indicator")
    if indicator is None:
        indicator = default_indicator
    return {
        "search": request.args.get("search", "").strip()[:100],
        "country": request.args.get("country", "").strip().upper(),
        "region": request.args.get("region", "").strip(),
        "income_level": request.args.get("income_level", "").strip(),
        "indicator": (indicator or "").strip(),
        "year_from": parse_number("year_from", int),
        "year_to": parse_number("year_to", int),
        "value_min": parse_number("value_min", float),
        "value_max": parse_number("value_max", float),
    }


def complete_options(options: dict[str, Any]) -> dict[str, Any]:
    if not options["indicators"]:
        settings = current_app.extensions["settings"]
        options["indicators"] = [
            {
                "indicator_code": code,
                "indicator_name": info["display_name"],
                "unit": info["unit"],
            }
            for code, info in settings.indicators.items()
        ]
    return options


def query_url(endpoint: str, **changes: Any) -> str:
    args = request.args.to_dict(flat=True)
    for key, value in changes.items():
        if value is None:
            args.pop(key, None)
        else:
            args[key] = value
    return url_for(endpoint, **args)


@web.get("/")
def dashboard():
    repo = repository()
    summary = repo.summary()
    latest = repo.latest_records()
    chart = AggregationService(repo).chart_data({"indicator": "SP.POP.TOTL"})
    return render_template(
        "dashboard.html",
        title="ダッシュボード",
        summary=summary,
        latest=latest,
        chart=chart,
    )


@web.get("/data")
def data_list():
    default_indicator = next(iter(current_app.extensions["settings"].indicators))
    filters = parse_filters(default_indicator=default_indicator)
    page = parse_number("page", int) or 1
    page_size = parse_number("page_size", int) or 25
    sort = request.args.get("sort", "year")
    sort = sort if sort in SORT_COLUMNS else "year"
    order = request.args.get("order", "desc").lower()
    order = order if order in {"asc", "desc"} else "desc"
    result = repository().list_records(filters, int(page), int(page_size), sort, order)
    options = complete_options(repository().filter_options())
    chart = AggregationService(repository()).chart_data(filters)

    sort_urls = {
        key: query_url(
            "web.data_list",
            sort=key,
            order="asc" if sort != key or order == "desc" else "desc",
            page=1,
        )
        for key in SORT_COLUMNS
    }
    page_urls = {
        page_number: query_url("web.data_list", page=page_number)
        for page_number in range(max(1, result["page"] - 2), min(result["pages"], result["page"] + 2) + 1)
    }
    return render_template(
        "data_list.html",
        title="データ一覧",
        filters=filters,
        result=result,
        options=options,
        sort=sort,
        order=order,
        sort_urls=sort_urls,
        page_urls=page_urls,
        previous_url=query_url("web.data_list", page=result["page"] - 1) if result["page"] > 1 else None,
        next_url=query_url("web.data_list", page=result["page"] + 1)
        if result["page"] < result["pages"]
        else None,
        chart=chart,
        csv_url=query_url("web.download_csv", page=None, sort=None, order=None),
    )


@web.get("/charts")
def charts():
    default_indicator = next(iter(current_app.extensions["settings"].indicators))
    filters = parse_filters(default_indicator=default_indicator)
    options = complete_options(repository().filter_options())
    chart = AggregationService(repository()).chart_data(filters)
    return render_template(
        "charts.html",
        title="グラフ分析",
        filters=filters,
        options=options,
        chart=chart,
    )


@web.get("/api/chart-data")
def chart_data():
    default_indicator = next(iter(current_app.extensions["settings"].indicators))
    filters = parse_filters(default_indicator=default_indicator)
    return jsonify(AggregationService(repository()).chart_data(filters))


@web.get("/data.csv")
def download_csv():
    default_indicator = next(iter(current_app.extensions["settings"].indicators))
    filters = parse_filters(default_indicator=default_indicator)
    records = repository().all_records(filters)
    columns = [
        "id",
        "country_code",
        "country_name",
        "region",
        "income_level",
        "indicator_code",
        "indicator_name",
        "value",
        "unit",
        "year",
        "period",
        "retrieved_at",
        "source_name",
        "source_url",
    ]
    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(records)
    payload = "\ufeff" + buffer.getvalue()
    return Response(
        payload,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=world_bank_data.csv"},
    )


@web.get("/health")
def health():
    summary = repository().summary()
    return jsonify({"status": "ok", "data_count": summary["data_count"]})
