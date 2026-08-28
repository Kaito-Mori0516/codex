import sqlite3

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


def test_initialize_migrates_existing_v1_database(tmp_path):
    database_path = tmp_path / "legacy.db"
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE indicator_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country_code TEXT NOT NULL,
                country_name TEXT NOT NULL,
                region TEXT NOT NULL,
                income_level TEXT NOT NULL,
                indicator_code TEXT NOT NULL,
                indicator_name TEXT NOT NULL,
                unit TEXT NOT NULL,
                value REAL NOT NULL,
                year INTEGER NOT NULL,
                period TEXT NOT NULL,
                retrieved_at TEXT NOT NULL,
                source_name TEXT NOT NULL,
                source_url TEXT NOT NULL,
                UNIQUE(country_code, indicator_code, year)
            )
            """
        )

    repository = DataRepository(database_path)
    repository.initialize()

    with repository.connection() as connection:
        columns = {
            str(row[1]) for row in connection.execute("PRAGMA table_info(indicator_values)")
        }
    assert {"indicator_name_en", "category"} <= columns
