from src.database.repository import DataRepository


def test_upsert_prevents_meaningless_duplicates(repository: DataRepository, sample_records):
    first = repository.save_records(sample_records)
    second = repository.save_records(sample_records)

    assert first.inserted_count == 4
    assert second.inserted_count == 0
    assert second.unchanged_count == 4
    assert repository.summary()["data_count"] == 4


def test_filter_sort_and_pagination(repository: DataRepository, sample_records):
    repository.save_records(sample_records)
    result = repository.list_records(
        {"country": "JPN", "year_from": 2021},
        page=1,
        page_size=10,
        sort="value",
        order="desc",
    )
    assert result["total"] == 1
    assert result["records"][0]["country_code"] == "JPN"
    assert result["records"][0]["year"] == 2021

    last_page = repository.list_records({}, page=999, page_size=10)
    assert last_page["page"] == last_page["pages"]
    assert last_page["records"]


def test_changed_value_is_updated(repository: DataRepository, sample_records):
    repository.save_records(sample_records)
    changed = {**sample_records[0], "value": 127.5}
    result = repository.save_records([changed])
    saved = repository.list_records({"country": "JPN", "year_from": 2020, "year_to": 2020})
    assert result.updated_count == 1
    assert saved["records"][0]["value"] == 127.5
