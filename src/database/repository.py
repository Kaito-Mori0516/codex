"""SQLite repository with allow-listed filtering and sorting."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


class DatabaseError(RuntimeError):
    """Wraps low-level SQLite failures with a safe application error."""


@dataclass(frozen=True)
class SaveResult:
    inserted_count: int
    updated_count: int
    unchanged_count: int


SORT_COLUMNS = {
    "country": "country_name",
    "region": "region",
    "indicator": "indicator_name",
    "year": "year",
    "value": "value",
    "retrieved": "retrieved_at",
}


class DataRepository:
    def __init__(self, database_path: Path | str) -> None:
        self.database_path = Path(database_path)
        self.schema_path = Path(__file__).with_name("schema.sql")

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.database_path, timeout=10)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 10000")
            yield connection
            connection.commit()
        except sqlite3.Error as exc:
            raise DatabaseError(str(exc)) from exc
        finally:
            if "connection" in locals():
                connection.close()

    def initialize(self) -> None:
        try:
            schema = self.schema_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise DatabaseError(f"Could not read database schema: {exc}") from exc
        with self.connection() as connection:
            connection.executescript(schema)
            # Additive migration for databases created by World Data Lens v1.
            # SQLite's CREATE TABLE IF NOT EXISTS does not add new columns.
            columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(indicator_values)")
            }
            if "indicator_name_en" not in columns:
                connection.execute(
                    "ALTER TABLE indicator_values "
                    "ADD COLUMN indicator_name_en TEXT NOT NULL DEFAULT ''"
                )
            if "category" not in columns:
                connection.execute(
                    "ALTER TABLE indicator_values "
                    "ADD COLUMN category TEXT NOT NULL DEFAULT 'その他'"
                )

    def start_update_run(self, started_at: str) -> int:
        with self.connection() as connection:
            cursor = connection.execute(
                "INSERT INTO update_runs (started_at, status) VALUES (?, 'running')", (started_at,)
            )
            return int(cursor.lastrowid)

    def finish_update_run(self, run_id: int, completed_at: str, result: dict[str, Any]) -> None:
        with self.connection() as connection:
            connection.execute(
                """
                UPDATE update_runs
                   SET completed_at = ?, status = ?, fetched_count = ?, inserted_count = ?,
                       updated_count = ?, unchanged_count = ?, skipped_count = ?,
                       failure_count = ?, message = ?
                 WHERE id = ?
                """,
                (
                    completed_at,
                    result["status"],
                    result["fetched_count"],
                    result["inserted_count"],
                    result["updated_count"],
                    result["unchanged_count"],
                    result["skipped_count"],
                    result["failure_count"],
                    result["message"],
                    run_id,
                ),
            )

    def save_records(self, records: list[dict[str, Any]]) -> SaveResult:
        if not records:
            return SaveResult(0, 0, 0)

        keys = [(r["country_code"], r["indicator_code"], r["year"]) for r in records]
        inserted = updated = unchanged = 0
        with self.connection() as connection:
            existing: dict[tuple[str, str, int], float] = {}
            for chunk_start in range(0, len(keys), 300):
                chunk = keys[chunk_start : chunk_start + 300]
                placeholders = ",".join("(?, ?, ?)" for _ in chunk)
                params = [part for key in chunk for part in key]
                rows = connection.execute(
                    f"""
                    SELECT country_code, indicator_code, year, value
                      FROM indicator_values
                     WHERE (country_code, indicator_code, year) IN ({placeholders})
                    """,
                    params,
                ).fetchall()
                existing.update(
                    {(row["country_code"], row["indicator_code"], row["year"]): row["value"] for row in rows}
                )

            for record in records:
                key = (record["country_code"], record["indicator_code"], record["year"])
                if key not in existing:
                    inserted += 1
                elif existing[key] == record["value"]:
                    unchanged += 1
                else:
                    updated += 1

            columns = (
                "country_code",
                "country_name",
                "region",
                "income_level",
                "indicator_code",
                "indicator_name",
                "indicator_name_en",
                "category",
                "unit",
                "value",
                "year",
                "period",
                "retrieved_at",
                "source_name",
                "source_url",
            )
            placeholders = ", ".join("?" for _ in columns)
            connection.executemany(
                f"""
                INSERT INTO indicator_values ({', '.join(columns)})
                VALUES ({placeholders})
                ON CONFLICT(country_code, indicator_code, year) DO UPDATE SET
                    country_name = excluded.country_name,
                    region = excluded.region,
                    income_level = excluded.income_level,
                    indicator_name = excluded.indicator_name,
                    indicator_name_en = excluded.indicator_name_en,
                    category = excluded.category,
                    unit = excluded.unit,
                    value = excluded.value,
                    period = excluded.period,
                    retrieved_at = excluded.retrieved_at,
                    source_name = excluded.source_name,
                    source_url = excluded.source_url
                """,
                [
                    tuple(
                        (
                            record.get("indicator_name_en")
                            or record.get("indicator_name")
                            or ""
                        )
                        if column == "indicator_name_en"
                        else (record.get("category") or "その他")
                        if column == "category"
                        else record[column]
                        for column in columns
                    )
                    for record in records
                ],
            )

        return SaveResult(inserted, updated, unchanged)

    def list_records(
        self,
        filters: dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 25,
        sort: str = "year",
        order: str = "desc",
    ) -> dict[str, Any]:
        filters = filters or {}
        where_sql, params = self._build_where(filters)
        sort_column = SORT_COLUMNS.get(sort, "year")
        direction = "ASC" if order.lower() == "asc" else "DESC"
        page = max(1, page)
        page_size = min(100, max(10, page_size))

        with self.connection() as connection:
            total = int(
                connection.execute(
                    f"SELECT COUNT(*) FROM indicator_values {where_sql}", params
                ).fetchone()[0]
            )
            pages = max(1, (total + page_size - 1) // page_size)
            page = min(page, pages)
            rows = connection.execute(
                f"""
                SELECT * FROM indicator_values {where_sql}
                 ORDER BY {sort_column} {direction}, id ASC
                 LIMIT ? OFFSET ?
                """,
                [*params, page_size, (page - 1) * page_size],
            ).fetchall()

        return {
            "records": [dict(row) for row in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
        }

    def all_records(self, filters: dict[str, Any] | None = None, limit: int = 20000) -> list[dict[str, Any]]:
        where_sql, params = self._build_where(filters or {})
        with self.connection() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM indicator_values {where_sql}
                 ORDER BY year ASC, country_name ASC
                 LIMIT ?
                """,
                [*params, limit],
            ).fetchall()
        return [dict(row) for row in rows]

    def summary(self) -> dict[str, Any]:
        with self.connection() as connection:
            values = connection.execute(
                """
                SELECT COUNT(*) AS data_count,
                       COUNT(DISTINCT country_code) AS country_count,
                       COUNT(DISTINCT region) AS region_count,
                       COUNT(DISTINCT indicator_code) AS indicator_count,
                       MAX(year) AS latest_year,
                       MAX(retrieved_at) AS last_retrieved_at
                  FROM indicator_values
                """
            ).fetchone()
            latest_run = connection.execute(
                "SELECT * FROM update_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
        result = dict(values)
        result["latest_run"] = dict(latest_run) if latest_run else None
        return result

    def latest_records(self, limit: int = 8) -> list[dict[str, Any]]:
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM indicator_values
                 ORDER BY year DESC, retrieved_at DESC, country_name ASC
                 LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def filter_options(self) -> dict[str, list[dict[str, str]] | list[str]]:
        with self.connection() as connection:
            countries = connection.execute(
                "SELECT DISTINCT country_code, country_name FROM indicator_values ORDER BY country_name"
            ).fetchall()
            indicators = connection.execute(
                """
                SELECT DISTINCT indicator_code, indicator_name, unit
                  FROM indicator_values ORDER BY indicator_name
                """
            ).fetchall()
            regions = connection.execute(
                "SELECT DISTINCT region FROM indicator_values ORDER BY region"
            ).fetchall()
            incomes = connection.execute(
                "SELECT DISTINCT income_level FROM indicator_values ORDER BY income_level"
            ).fetchall()
        return {
            "countries": [dict(row) for row in countries],
            "indicators": [dict(row) for row in indicators],
            "regions": [row[0] for row in regions],
            "income_levels": [row[0] for row in incomes],
        }

    @staticmethod
    def _build_where(filters: dict[str, Any]) -> tuple[str, list[Any]]:
        clauses: list[str] = []
        params: list[Any] = []

        search = str(filters.get("search") or "").strip()
        if search:
            pattern = f"%{search}%"
            clauses.append(
                "(country_name LIKE ? OR country_code LIKE ? OR indicator_name LIKE ? "
                "OR indicator_code LIKE ? OR region LIKE ? OR income_level LIKE ?)"
            )
            params.extend([pattern] * 6)

        exact_filters = {
            "country": "country_code",
            "region": "region",
            "income_level": "income_level",
            "indicator": "indicator_code",
        }
        for filter_name, column in exact_filters.items():
            value = filters.get(filter_name)
            if value:
                clauses.append(f"{column} = ?")
                params.append(value)

        range_filters = {
            "year_from": ("year", ">="),
            "year_to": ("year", "<="),
            "value_min": ("value", ">="),
            "value_max": ("value", "<="),
        }
        for filter_name, (column, operator) in range_filters.items():
            value = filters.get(filter_name)
            if value is not None and value != "":
                clauses.append(f"{column} {operator} ?")
                params.append(value)

        return ("WHERE " + " AND ".join(clauses) if clauses else ""), params
