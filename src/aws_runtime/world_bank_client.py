"""World Bank client for Lambda with raw-response archiving to S3."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import boto3

from src.acquisition.errors import DataAcquisitionError


LOGGER = logging.getLogger(__name__)


class WorldBankS3Client:
    """Fetches the official API and archives each successful raw JSON body."""

    def __init__(
        self,
        base_url: str,
        raw_bucket_name: str,
        timeout: float = 20,
        max_retries: int = 3,
        backoff_factor: float = 0.8,
        request_interval: float = 0.5,
        user_agent: str = "WorldDataLens/1.0",
        s3_client: Any | None = None,
        opener: Callable[..., Any] = urlopen,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.raw_bucket_name = raw_bucket_name
        self.timeout = timeout
        self.max_retries = max(0, max_retries)
        self.backoff_factor = max(0, backoff_factor)
        self.request_interval = max(0, request_interval)
        self.user_agent = user_agent
        self.s3 = s3_client or boto3.client("s3")
        self.opener = opener
        self.sleep = sleep

    def fetch_country_metadata(self) -> list[Any]:
        payload, body, source_url = self._get_json(
            "/country", {"format": "json", "per_page": 400}
        )
        self._archive("country-metadata", body, source_url)
        return payload

    def fetch_indicator(
        self,
        country_codes: tuple[str, ...],
        indicator_code: str,
        start_year: int,
        end_year: int,
    ) -> tuple[list[Any], str]:
        countries = ";".join(country_codes)
        payload, body, source_url = self._get_json(
            f"/country/{countries}/indicator/{indicator_code}",
            {
                "date": f"{start_year}:{end_year}",
                "format": "json",
                "per_page": 20000,
            },
        )
        self._archive(indicator_code, body, source_url)
        return payload, source_url

    def _get_json(
        self, path: str, params: dict[str, Any]
    ) -> tuple[list[Any], bytes, str]:
        source_url = f"{self.base_url}{path}?{urlencode(params)}"
        request = Request(
            source_url,
            headers={"User-Agent": self.user_agent, "Accept": "application/json"},
        )
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    body = response.read()
                payload = json.loads(body.decode("utf-8"))
                if not isinstance(payload, list) or len(payload) < 2:
                    raise DataAcquisitionError(
                        "World Bank API response structure changed or is incomplete"
                    )
                if payload[1] is None:
                    payload = [payload[0], []]
                if not isinstance(payload[1], list):
                    raise DataAcquisitionError("World Bank API data section is not a list")
                if self.request_interval:
                    self.sleep(self.request_interval)
                return payload, body, source_url
            except HTTPError as exc:
                last_error = exc
                if exc.code == 404:
                    raise DataAcquisitionError(f"API endpoint not found (404): {source_url}") from exc
                retryable = exc.code == 429 or 500 <= exc.code
                if not retryable or attempt >= self.max_retries:
                    raise DataAcquisitionError(
                        f"World Bank API returned HTTP {exc.code}: {source_url}"
                    ) from exc
                self.sleep(self._retry_delay(attempt, exc.headers.get("Retry-After")))
            except URLError as exc:
                last_error = exc
                if attempt >= self.max_retries:
                    raise DataAcquisitionError(f"Connection failed for {source_url}: {exc}") from exc
                self.sleep(self._retry_delay(attempt, None))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise DataAcquisitionError("World Bank API returned invalid JSON") from exc

        raise DataAcquisitionError(f"World Bank API request failed: {last_error}")

    def _archive(self, dataset: str, body: bytes, source_url: str) -> None:
        now = datetime.now(timezone.utc)
        safe_dataset = "".join(
            character if character.isalnum() or character in {"-", "."} else "-"
            for character in dataset
        )
        key = (
            f"raw/{now:%Y/%m/%d}/{safe_dataset}/"
            f"{now:%Y%m%dT%H%M%S%fZ}.json"
        )
        self.s3.put_object(
            Bucket=self.raw_bucket_name,
            Key=key,
            Body=body,
            ContentType="application/json",
            Metadata={"source-url": source_url[:1900]},
        )
        LOGGER.info("Archived raw World Bank response", extra={"s3_key": key})

    def _retry_delay(self, attempt: int, retry_after: str | None) -> float:
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                try:
                    retry_at = parsedate_to_datetime(retry_after)
                    if retry_at.tzinfo is None:
                        retry_at = retry_at.replace(tzinfo=timezone.utc)
                    return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
                except (TypeError, ValueError):
                    pass
        return self.backoff_factor * (2**attempt)
