import pytest

from src.database.repository import DataRepository
from src.services.aggregation_service import AggregationService


def test_chart_aggregation(repository: DataRepository, sample_records):
    repository.save_records(sample_records)
    result = AggregationService(repository).chart_data({"indicator": "SP.POP.TOTL"})

    assert result["latest_year"] == 2021
    assert result["time_series"][0]["value"] == pytest.approx((126 + 331) / 2)
    assert len(result["region_comparison"]) == 2
    assert result["ranking"][0]["country_code"] == "USA"
