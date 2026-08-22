"""DynamoDB repository for indicator values and update-run metadata."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import uuid4

import boto3
from boto3.dynamodb.conditions import Attr, Key
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer

from src.database.repository import SaveResult


ENTITY_TYPE = "indicator_value"
INDICATOR_YEAR_INDEX = "indicator-year-index"


def _record_key(record: dict[str, Any]) -> dict[str, str]:
    return {
        "pk": (
            f"COUNTRY#{record['country_code']}#"
            f"INDICATOR#{record['indicator_code']}"
        ),
        "sk": f"YEAR#{int(record['year']):04d}",
    }


def _to_python(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    if isinstance(value, list):
        return [_to_python(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_python(item) for key, item in value.items()}
    return value


class DynamoDataRepository:
    def __init__(self, table_name: str, dynamodb_resource: Any | None = None) -> None:
        resource = dynamodb_resource or boto3.resource("dynamodb")
        self.table = resource.Table(table_name)
        self.table_name = table_name
        self._deserializer = TypeDeserializer()
        self._serializer = TypeSerializer()

    def start_update_run(self, started_at: str) -> str:
        run_id = f"{started_at}#{uuid4().hex[:12]}"
        self.table.put_item(
            Item={
                "pk": "UPDATE_RUN",
                "sk": f"RUN#{run_id}",
                "entity_type": "update_run",
                "started_at": started_at,
                "status": "running",
            }
        )
        return run_id

    def finish_update_run(
        self, run_id: str, completed_at: str, result: dict[str, Any]
    ) -> None:
        self.table.update_item(
            Key={"pk": "UPDATE_RUN", "sk": f"RUN#{run_id}"},
            UpdateExpression=(
                "SET completed_at = :completed, #status = :status, fetched_count = :fetched, "
                "inserted_count = :inserted, updated_count = :updated, "
                "unchanged_count = :unchanged, skipped_count = :skipped, "
                "failure_count = :failures, #message = :message"
            ),
            ExpressionAttributeNames={"#status": "status", "#message": "message"},
            ExpressionAttributeValues={
                ":completed": completed_at,
                ":status": result["status"],
                ":fetched": result["fetched_count"],
                ":inserted": result["inserted_count"],
                ":updated": result["updated_count"],
                ":unchanged": result["unchanged_count"],
                ":skipped": result["skipped_count"],
                ":failures": result["failure_count"],
                ":message": result["message"],
            },
        )

    def save_records(self, records: list[dict[str, Any]]) -> SaveResult:
        if not records:
            return SaveResult(0, 0, 0)

        existing = self._batch_get([_record_key(record) for record in records])
        inserted = updated = unchanged = 0
        with self.table.batch_writer(overwrite_by_pkeys=["pk", "sk"]) as batch:
            for record in records:
                key = _record_key(record)
                previous = existing.get((key["pk"], key["sk"]))
                new_value = Decimal(str(record["value"]))
                if previous is None:
                    inserted += 1
                elif previous.get("value") == new_value:
                    unchanged += 1
                else:
                    updated += 1
                batch.put_item(Item=self._item_from_record(record))
        return SaveResult(inserted, updated, unchanged)

    def _batch_get(self, keys: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, Any]]:
        existing: dict[tuple[str, str], dict[str, Any]] = {}
        client = self.table.meta.client
        for start in range(0, len(keys), 100):
            serialized_keys = [
                {
                    name: self._serializer.serialize(value)
                    for name, value in key.items()
                }
                for key in keys[start : start + 100]
            ]
            request_items: dict[str, Any] = {
                self.table_name: {"Keys": serialized_keys}
            }
            while request_items:
                response = client.batch_get_item(RequestItems=request_items)
                for item in response.get("Responses", {}).get(self.table_name, []):
                    decoded = {
                        name: self._deserializer.deserialize(value)
                        for name, value in item.items()
                    }
                    existing[(decoded["pk"], decoded["sk"])] = decoded
                request_items = response.get("UnprocessedKeys", {})
        return existing

    @staticmethod
    def _item_from_record(record: dict[str, Any]) -> dict[str, Any]:
        key = _record_key(record)
        return {
            **key,
            "entity_type": ENTITY_TYPE,
            "gsi1pk": f"INDICATOR#{record['indicator_code']}",
            "gsi1sk": (
                f"YEAR#{int(record['year']):04d}#"
                f"COUNTRY#{record['country_code']}"
            ),
            **{
                name: Decimal(str(value)) if name == "value" else value
                for name, value in record.items()
            },
        }

    def all_records(
        self, filters: dict[str, Any] | None = None, limit: int = 20000
    ) -> list[dict[str, Any]]:
        filters = filters or {}
        country = str(filters.get("country") or "").upper()
        indicator = str(filters.get("indicator") or "")
        year_from = int(filters.get("year_from") or 0)
        year_to = int(filters.get("year_to") or 9999)
        limit = max(1, min(int(limit), 20000))

        if country and indicator:
            request: dict[str, Any] = {
                "KeyConditionExpression": Key("pk").eq(
                    f"COUNTRY#{country}#INDICATOR#{indicator}"
                )
                & Key("sk").between(
                    f"YEAR#{year_from:04d}", f"YEAR#{year_to:04d}"
                )
            }
            operation = self.table.query
        elif indicator:
            request = {
                "IndexName": INDICATOR_YEAR_INDEX,
                "KeyConditionExpression": Key("gsi1pk").eq(f"INDICATOR#{indicator}")
                & Key("gsi1sk").between(
                    f"YEAR#{year_from:04d}", f"YEAR#{year_to:04d}~"
                ),
            }
            operation = self.table.query
        else:
            request = {"FilterExpression": Attr("entity_type").eq(ENTITY_TYPE)}
            operation = self.table.scan

        items: list[dict[str, Any]] = []
        while True:
            response = operation(**request)
            items.extend(response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if not last_key or len(items) >= limit:
                break
            request["ExclusiveStartKey"] = last_key

        records = [self._public_record(item) for item in items]
        records = [record for record in records if self._matches(record, filters)]
        records.sort(key=lambda row: (int(row["year"]), str(row["country_name"])))
        return records[:limit]

    @staticmethod
    def _public_record(item: dict[str, Any]) -> dict[str, Any]:
        hidden = {"pk", "sk", "gsi1pk", "gsi1sk", "entity_type"}
        return _to_python({key: value for key, value in item.items() if key not in hidden})

    @staticmethod
    def _matches(record: dict[str, Any], filters: dict[str, Any]) -> bool:
        exact = {
            "country": "country_code",
            "indicator": "indicator_code",
            "region": "region",
            "income_level": "income_level",
        }
        for filter_name, field in exact.items():
            value = filters.get(filter_name)
            if value and str(record.get(field, "")) != str(value):
                return False
        year = int(record["year"])
        value = float(record["value"])
        if filters.get("year_from") not in {None, ""} and year < int(filters["year_from"]):
            return False
        if filters.get("year_to") not in {None, ""} and year > int(filters["year_to"]):
            return False
        if filters.get("value_min") not in {None, ""} and value < float(filters["value_min"]):
            return False
        if filters.get("value_max") not in {None, ""} and value > float(filters["value_max"]):
            return False
        search = str(filters.get("search") or "").strip().lower()
        if search:
            haystack = " ".join(
                str(record.get(field, ""))
                for field in (
                    "country_code",
                    "country_name",
                    "region",
                    "income_level",
                    "indicator_code",
                    "indicator_name",
                )
            ).lower()
            if search not in haystack:
                return False
        return True

    def filter_options(self) -> dict[str, Any]:
        records = self.all_records(limit=20000)
        countries = {
            (str(row["country_code"]), str(row["country_name"])) for row in records
        }
        indicators = {
            (
                str(row["indicator_code"]),
                str(row["indicator_name"]),
                str(row["unit"]),
            )
            for row in records
        }
        return {
            "countries": [
                {"country_code": code, "country_name": name}
                for code, name in sorted(countries, key=lambda item: item[1])
            ],
            "indicators": [
                {"indicator_code": code, "indicator_name": name, "unit": unit}
                for code, name, unit in sorted(indicators, key=lambda item: item[1])
            ],
        }

    def summary(self) -> dict[str, int]:
        total = 0
        request: dict[str, Any] = {
            "Select": "COUNT",
            "FilterExpression": Attr("entity_type").eq(ENTITY_TYPE),
        }
        while True:
            response = self.table.scan(**request)
            total += int(response.get("Count", 0))
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                break
            request["ExclusiveStartKey"] = last_key
        return {"data_count": total}
