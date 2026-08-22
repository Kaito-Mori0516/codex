"""Rate-limited client for the official World Bank Indicators API."""

from __future__ import annotations

import time
from typing import Any, Callable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.acquisition.errors import DataAcquisitionError


class WorldBankClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 20,
        max_retries: int = 3,
        backoff_factor: float = 0.8,
        request_interval: float = 0.5,
        user_agent: str = "OpenDataDashboard/1.0",
        session: requests.Session | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.request_interval = max(0, request_interval)
        self.sleep = sleep
        self.session = session or self._build_session(max_retries, backoff_factor)
        self.session.headers.update({"User-Agent": user_agent, "Accept": "application/json"})

    @staticmethod
    def _build_session(max_retries: int, backoff_factor: float) -> requests.Session:
        retry = Retry(
            total=max_retries,
            connect=max_retries,
            read=max_retries,
            status=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def fetch_country_metadata(self) -> list[Any]:
        return self._get_json("/country", {"format": "json", "per_page": 400})

    def fetch_indicator(
        self, country_codes: tuple[str, ...], indicator_code: str, start_year: int, end_year: int
    ) -> tuple[list[Any], str]:
        countries = ";".join(country_codes)
        path = f"/country/{countries}/indicator/{indicator_code}"
        params = {
            "date": f"{start_year}:{end_year}",
            "format": "json",
            "per_page": 20000,
        }
        payload = self._get_json(path, params)
        source_url = requests.Request("GET", f"{self.base_url}{path}", params=params).prepare().url
        return payload, str(source_url)

    def _get_json(self, path: str, params: dict[str, Any]) -> list[Any]:
        url = f"{self.base_url}{path}"
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
        except requests.RequestException as exc:
            raise DataAcquisitionError(f"Connection failed for {url}: {exc}") from exc

        if self.request_interval:
            self.sleep(self.request_interval)

        if response.status_code == 404:
            raise DataAcquisitionError(f"API endpoint not found (404): {response.url}")
        if response.status_code == 429:
            raise DataAcquisitionError(f"API rate limit reached (429): {response.url}")
        if 500 <= response.status_code:
            raise DataAcquisitionError(f"World Bank API server error ({response.status_code})")
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise DataAcquisitionError(
                f"World Bank API returned HTTP {response.status_code}: {response.url}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise DataAcquisitionError("World Bank API returned invalid JSON") from exc
        if not isinstance(payload, list) or len(payload) < 2:
            raise DataAcquisitionError("World Bank API response structure changed or is incomplete")
        if payload[1] is None:
            return [payload[0], []]
        if not isinstance(payload[1], list):
            raise DataAcquisitionError("World Bank API data section is not a list")
        return payload
