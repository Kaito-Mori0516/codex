from src.database.repository import DataRepository
from src.services.data_service import DataUpdateService


class FakeWorldBankClient:
    def __init__(self, country_payload, indicator_payload):
        self.country_payload = country_payload
        self.indicator_payload = indicator_payload

    def fetch_country_metadata(self):
        return self.country_payload

    def fetch_indicator(self, country_codes, indicator_code, start_year, end_year):
        return self.indicator_payload, "https://api.worldbank.org/v2/example"


def test_complete_update_flow(settings, repository: DataRepository, country_payload, indicator_payload):
    client = FakeWorldBankClient(country_payload, indicator_payload)
    result = DataUpdateService(settings, repository, client=client).update()

    assert result.status == "success"
    assert result.fetched_count == 4
    assert result.inserted_count == 4
    assert result.skipped_count == 1
    assert repository.summary()["data_count"] == 4
    assert repository.summary()["latest_run"]["status"] == "success"
