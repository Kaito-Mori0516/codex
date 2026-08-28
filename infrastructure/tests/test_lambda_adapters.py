import json
from base64 import b64decode
from decimal import Decimal
from types import SimpleNamespace

from src.aws_database.dynamodb_repository import _record_key
from src.aws_database.dynamodb_repository import DynamoDataRepository
from src.aws_handlers.api_handler import handle_event
from src.aws_runtime.world_bank_client import WorldBankS3Client


class FakeResponse:
    def __init__(self, payload):
        self.body = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body


class FakeS3:
    def __init__(self):
        self.objects = []

    def put_object(self, **kwargs):
        self.objects.append(kwargs)


class FakeRepository:
    def __init__(self):
        self.records = [
            {
                "country_code": "JPN",
                "country_name": "Japan",
                "region": "East Asia & Pacific",
                "income_level": "High income",
                "indicator_code": "SP.POP.TOTL",
                "indicator_name": "人口（総数）",
                "unit": "人",
                "value": 125.0,
                "year": 2021,
                "period": "2021-01-01",
                "retrieved_at": "2026-08-21T00:00:00+00:00",
                "source_name": "World Bank Indicators API",
                "source_url": "https://api.worldbank.org/v2/example",
            }
        ]

    def all_records(self, *_args, **_kwargs):
        return list(self.records)

    def summary(self):
        return {"data_count": 1}

    def filter_options(self):
        return {
            "countries": [{"country_code": "JPN", "country_name": "Japan"}],
            "indicators": [
                {
                    "indicator_code": "SP.POP.TOTL",
                    "indicator_name": "人口（総数）",
                    "unit": "人",
                }
            ],
        }


class FakeBatchWriter:
    def __init__(self):
        self.items = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def put_item(self, *, Item):
        self.items.append(Item)


class FakeDynamoClient:
    def __init__(self):
        self.request_items = None

    def batch_get_item(self, *, RequestItems):
        self.request_items = RequestItems
        return {"Responses": {"table": []}, "UnprocessedKeys": {}}


class FakeDynamoTable:
    def __init__(self):
        self.client = FakeDynamoClient()
        self.meta = SimpleNamespace(client=self.client)
        self.writer = FakeBatchWriter()

    def batch_writer(self, **_kwargs):
        return self.writer


class FakeDynamoResource:
    def __init__(self):
        self.table = FakeDynamoTable()

    def Table(self, _name):
        return self.table


def event(path, params=None):
    return {
        "requestContext": {"http": {"method": "GET", "path": path}},
        "queryStringParameters": params,
    }


def test_api_adapter_exposes_required_routes():
    repository = FakeRepository()
    assert json.loads(handle_event(event("/health"), repository)["body"])["data_count"] == 1
    assert json.loads(handle_event(event("/data"), repository)["body"])["total"] == 1
    assert json.loads(handle_event(event("/countries"), repository)["body"])["countries"]
    assert json.loads(handle_event(event("/indicators"), repository)["body"])["indicators"]
    assert json.loads(
        handle_event(event("/charts/timeseries"), repository)["body"]
    )["time_series"]
    assert json.loads(
        handle_event(event("/charts/ranking"), repository)["body"]
    )["ranking"]
    assert json.loads(handle_event(event("/api/catalog"), repository)["body"])[
        "indicators"
    ]
    assert json.loads(handle_event(event("/api/summary"), repository)["body"])[
        "indicator_count"
    ]


def test_api_adapter_generates_csv_and_excel_downloads():
    repository = FakeRepository()
    csv_response = handle_event(
        event("/api/export.csv", {"indicator": "SP.POP.TOTL"}), repository
    )
    xlsx_response = handle_event(
        event("/api/export.xlsx", {"indicator": "SP.POP.TOTL"}), repository
    )

    assert csv_response["isBase64Encoded"] is True
    assert b64decode(csv_response["body"]).startswith(b"\xef\xbb\xbf")
    assert xlsx_response["isBase64Encoded"] is True
    assert b64decode(xlsx_response["body"]).startswith(b"PK")


def test_lambda_world_bank_client_archives_raw_json():
    payload = [{"total": 0}, []]
    s3 = FakeS3()
    client = WorldBankS3Client(
        "https://api.worldbank.org/v2",
        "raw-bucket",
        request_interval=0,
        s3_client=s3,
        opener=lambda *_args, **_kwargs: FakeResponse(payload),
    )
    assert client.fetch_country_metadata() == payload
    assert len(s3.objects) == 1
    assert s3.objects[0]["Bucket"] == "raw-bucket"
    assert s3.objects[0]["Key"].startswith("raw/")


def test_dynamodb_key_preserves_local_uniqueness():
    record = {
        "country_code": "JPN",
        "indicator_code": "SP.POP.TOTL",
        "year": 2021,
    }
    assert _record_key(record) == {
        "pk": "COUNTRY#JPN#INDICATOR#SP.POP.TOTL",
        "sk": "YEAR#2021",
    }


def test_dynamodb_repository_serializes_batch_keys_and_float_values():
    resource = FakeDynamoResource()
    repository = DynamoDataRepository("table", dynamodb_resource=resource)
    record = dict(FakeRepository().records[0])

    result = repository.save_records([record])

    assert result.inserted_count == 1
    request_key = resource.table.client.request_items["table"]["Keys"][0]
    assert request_key["pk"] == {"S": "COUNTRY#JPN#INDICATOR#SP.POP.TOTL"}
    assert resource.table.writer.items[0]["value"] == Decimal("125.0")
