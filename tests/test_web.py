from src.database.repository import DataRepository
from src.web import create_app


def test_main_pages_csv_and_health(settings, sample_records):
    repository = DataRepository(settings.database_path)
    repository.initialize()
    repository.save_records(sample_records)
    app = create_app({"SETTINGS": settings, "TESTING": True})
    client = app.test_client()

    assert client.get("/").status_code == 200
    assert client.get("/data?indicator=SP.POP.TOTL&country=JPN").status_code == 200
    assert client.get("/charts?indicator=SP.POP.TOTL").status_code == 200

    chart_response = client.get("/api/chart-data?indicator=SP.POP.TOTL&region=North%20America")
    assert chart_response.status_code == 200
    assert chart_response.get_json()["ranking"][0]["country_code"] == "USA"

    csv_response = client.get("/data.csv?indicator=SP.POP.TOTL&country=JPN")
    assert csv_response.status_code == 200
    assert "text/csv" in csv_response.content_type
    assert "JPN" in csv_response.get_data(as_text=True)

    assert client.get("/health").get_json() == {"status": "ok", "data_count": 4}
