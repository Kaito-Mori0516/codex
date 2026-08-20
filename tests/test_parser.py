from src.acquisition.parser import parse_country_metadata, parse_indicator_payload


def test_transform_valid_rows_and_counts_missing(country_payload, indicator_payload):
    countries = parse_country_metadata(country_payload, ("JPN", "USA"))
    result = parse_indicator_payload(
        indicator_payload,
        countries,
        "SP.POP.TOTL",
        {"display_name": "人口（総数）", "unit": "人"},
        "2026-08-20T00:00:00+00:00",
        "https://api.worldbank.org/v2/example",
    )

    assert len(result.records) == 4
    assert result.skipped_count == 1
    assert result.failure_count == 0
    assert result.records[0]["country_name"] == "Japan"
    assert result.records[0]["period"] == "2021-01-01"
    assert result.records[0]["source_name"] == "World Bank Indicators API"


def test_invalid_numeric_value_is_counted_as_failure(country_payload):
    countries = parse_country_metadata(country_payload, ("JPN", "USA"))
    payload = [{"total": 1}, [{"countryiso3code": "JPN", "date": "bad", "value": "x"}]]
    result = parse_indicator_payload(
        payload,
        countries,
        "SP.POP.TOTL",
        {"display_name": "人口（総数）", "unit": "人"},
        "2026-08-20T00:00:00+00:00",
        "https://api.worldbank.org/v2/example",
    )
    assert result.records == []
    assert result.failure_count == 1
