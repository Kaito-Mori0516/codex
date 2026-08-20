from __future__ import annotations

import pytest

from src.acquisition.client import DataAcquisitionError, WorldBankClient


class FakeResponse:
    def __init__(self, payload, status_code=200, url="https://example.test/api"):
        self.payload = payload
        self.status_code = status_code
        self.url = url

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.headers = {}
        self.calls = []

    def get(self, url, params, timeout):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        return self.response


def test_fetch_indicator_uses_structured_api_and_access_controls(indicator_payload):
    session = FakeSession(FakeResponse(indicator_payload))
    client = WorldBankClient(
        "https://api.worldbank.org/v2",
        timeout=12,
        request_interval=0,
        user_agent="TestDashboard/1.0",
        session=session,
    )

    payload, source_url = client.fetch_indicator(("JPN", "USA"), "SP.POP.TOTL", 2020, 2021)

    assert payload == indicator_payload
    assert session.calls[0]["timeout"] == 12
    assert session.calls[0]["params"]["date"] == "2020:2021"
    assert session.headers["User-Agent"] == "TestDashboard/1.0"
    assert "SP.POP.TOTL" in source_url


@pytest.mark.parametrize("status", [404, 429, 500, 503])
def test_http_errors_are_reported_without_crashing_process(status):
    session = FakeSession(FakeResponse([], status_code=status))
    client = WorldBankClient(
        "https://api.worldbank.org/v2", request_interval=0, session=session
    )
    with pytest.raises(DataAcquisitionError):
        client.fetch_country_metadata()


def test_changed_response_structure_is_rejected():
    session = FakeSession(FakeResponse({"unexpected": "shape"}))
    client = WorldBankClient(
        "https://api.worldbank.org/v2", request_interval=0, session=session
    )
    with pytest.raises(DataAcquisitionError, match="structure"):
        client.fetch_country_metadata()
