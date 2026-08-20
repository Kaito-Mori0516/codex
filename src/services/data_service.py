"""Orchestrates acquire -> transform -> persist without web dependencies."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from src.acquisition.client import DataAcquisitionError, WorldBankClient
from src.acquisition.parser import parse_country_metadata, parse_indicator_payload
from src.config import Settings
from src.database.repository import DataRepository


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class UpdateResult:
    status: str = "failed"
    fetched_count: int = 0
    inserted_count: int = 0
    updated_count: int = 0
    unchanged_count: int = 0
    skipped_count: int = 0
    failure_count: int = 0
    message: str = ""

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)

    def to_console_text(self) -> str:
        return (
            f"Status: {self.status}\n"
            f"取得・整形成功: {self.fetched_count}件\n"
            f"新規保存: {self.inserted_count}件\n"
            f"更新: {self.updated_count}件\n"
            f"変更なし: {self.unchanged_count}件\n"
            f"欠損のため除外: {self.skipped_count}件\n"
            f"失敗: {self.failure_count}件\n"
            f"Message: {self.message}"
        )


class DataUpdateService:
    def __init__(
        self,
        settings: Settings,
        repository: DataRepository,
        client: WorldBankClient | None = None,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.client = client or WorldBankClient(
            base_url=settings.api_base_url,
            timeout=settings.request_timeout,
            max_retries=settings.max_retries,
            backoff_factor=settings.backoff_factor,
            request_interval=settings.request_interval,
            user_agent=settings.user_agent,
        )

    def update(self) -> UpdateResult:
        started_at = utc_now()
        run_id = self.repository.start_update_run(started_at)
        result = UpdateResult()
        errors: list[str] = []

        try:
            country_payload = self.client.fetch_country_metadata()
            countries = parse_country_metadata(country_payload, self.settings.countries)

            records = []
            for indicator_code, indicator in self.settings.indicators.items():
                try:
                    payload, source_url = self.client.fetch_indicator(
                        self.settings.countries,
                        indicator_code,
                        self.settings.start_year,
                        self.settings.end_year,
                    )
                    transformed = parse_indicator_payload(
                        payload,
                        countries,
                        indicator_code,
                        indicator,
                        started_at,
                        source_url,
                    )
                    records.extend(transformed.records)
                    result.skipped_count += transformed.skipped_count
                    result.failure_count += transformed.failure_count
                except (DataAcquisitionError, ValueError) as exc:
                    result.failure_count += 1
                    errors.append(f"{indicator_code}: {exc}")

            result.fetched_count = len(records)
            saved = self.repository.save_records(records)
            result.inserted_count = saved.inserted_count
            result.updated_count = saved.updated_count
            result.unchanged_count = saved.unchanged_count

            if records and not errors and result.failure_count == 0:
                result.status = "success"
                result.message = "All configured indicators were updated successfully."
            elif records:
                result.status = "partial"
                result.message = "Some data was saved, but one or more records or indicators failed."
            else:
                result.status = "failed"
                result.message = "No records were saved."
        except (DataAcquisitionError, ValueError) as exc:
            result.failure_count += 1
            errors.append(str(exc))
            result.message = "Could not retrieve required country metadata."
        finally:
            if errors:
                safe_errors = " | ".join(errors)
                result.message = f"{result.message} Details: {safe_errors}"[:1000]
            self.repository.finish_update_run(run_id, utc_now(), result.to_dict())

        return result
