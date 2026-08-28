from io import BytesIO
from zipfile import ZipFile

from src.exports import build_csv, build_xlsx


def test_csv_has_japanese_headers_and_excel_bom(sample_records):
    payload = build_csv(sample_records)

    assert payload.startswith(b"\xef\xbb\xbf")
    text = payload.decode("utf-8-sig")
    assert "国コード" in text
    assert "JPN" in text
    assert "World Bank Indicators API" in text


def test_xlsx_contains_summary_data_and_methodology_sheets(sample_records):
    payload = build_xlsx(
        sample_records,
        filters={"indicator": "SP.POP.TOTL", "year_from": 2020},
        generated_at="2026-08-28T00:00:00+00:00",
    )

    with ZipFile(BytesIO(payload)) as workbook:
        names = set(workbook.namelist())
        assert "xl/workbook.xml" in names
        assert "xl/styles.xml" in names
        assert "xl/worksheets/sheet2.xml" in names
        workbook_xml = workbook.read("xl/workbook.xml").decode()
        data_xml = workbook.read("xl/worksheets/sheet2.xml").decode()

    assert 'name="Summary"' in workbook_xml
    assert 'name="Data"' in workbook_xml
    assert 'name="Methodology"' in workbook_xml
    assert "国コード" in data_xml
    assert "JPN" in data_xml
    assert "autoFilter" in data_xml
