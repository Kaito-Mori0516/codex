"""Generate presentation-ready CSV and XLSX files using the Python standard library."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from io import BytesIO, StringIO
from math import isfinite
from typing import Any, Iterable
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


EXPORT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("country_code", "国コード"),
    ("country_name", "国名"),
    ("region", "地域"),
    ("income_level", "所得区分"),
    ("category", "カテゴリー"),
    ("indicator_code", "指標コード"),
    ("indicator_name", "指標名"),
    ("indicator_name_en", "指標名（英語）"),
    ("value", "値"),
    ("unit", "単位"),
    ("year", "年"),
    ("retrieved_at", "取得日時（UTC）"),
    ("source_name", "データソース"),
    ("source_url", "出典URL"),
)


def _normalized_rows(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        row = {key: record.get(key, "") for key, _label in EXPORT_COLUMNS}
        row["category"] = row["category"] or "その他"
        row["indicator_name_en"] = row["indicator_name_en"] or row["indicator_name"]
        rows.append(row)
    return rows


def build_csv(records: Iterable[dict[str, Any]]) -> bytes:
    """Return a UTF-8 BOM CSV that opens cleanly in Japanese Excel."""

    rows = _normalized_rows(records)
    buffer = StringIO(newline="")
    writer = csv.DictWriter(
        buffer,
        fieldnames=[key for key, _label in EXPORT_COLUMNS],
        extrasaction="ignore",
    )
    writer.writerow({key: label for key, label in EXPORT_COLUMNS})
    writer.writerows(rows)
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def build_xlsx(
    records: Iterable[dict[str, Any]],
    *,
    filters: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> bytes:
    """Build a dependency-free XLSX workbook with data, summary, and notes sheets."""

    rows = _normalized_rows(records)
    generated_at = generated_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    filters = {key: value for key, value in (filters or {}).items() if value not in {None, ""}}

    summary_rows: list[list[Any]] = [
        ["World Data Lens | Business Data Export"],
        [],
        ["生成日時（UTC）", generated_at],
        ["データ件数", len(rows)],
        ["対象条件", _filter_description(filters)],
        ["利用目的", "企業資料・市場調査・国際比較向けの整形済みオープンデータ"],
        [],
        ["重要事項"],
        ["数値を意思決定に使用する際は、出典URLとWorld Bankの指標定義を確認してください。"],
        ["欠損値や更新時期は国・指標によって異なります。"],
        ["本データはWorld Bankの公式製品ではありません。"],
    ]
    data_rows: list[list[Any]] = [
        [label for _key, label in EXPORT_COLUMNS],
        *[[row[key] for key, _label in EXPORT_COLUMNS] for row in rows],
    ]
    notes_rows = [
        ["項目", "説明"],
        ["データ取得元", "World Bank Indicators API"],
        ["ライセンス", "原則 CC BY 4.0。個別指標のメタデータに別条件がないか確認してください。"],
        ["一意キー", "国コード + 指標コード + 年"],
        ["値", "指標ごとに単位が異なります。異なる指標の値を直接合算しないでください。"],
        ["取得日時", "World Data LensがAPIレスポンスを取得したUTC日時"],
        ["出典URL", "再確認・引用に使用できるWorld Bank API URL"],
        [],
        ["列名", "内容"],
        *[[label, _column_description(key)] for key, label in EXPORT_COLUMNS],
    ]

    workbook = BytesIO()
    with ZipFile(workbook, "w", ZIP_DEFLATED) as archive:
        _write(archive, "[Content_Types].xml", _content_types())
        _write(archive, "_rels/.rels", _root_relationships())
        _write(archive, "docProps/app.xml", _app_properties())
        _write(archive, "docProps/core.xml", _core_properties(generated_at))
        _write(archive, "xl/workbook.xml", _workbook())
        _write(archive, "xl/_rels/workbook.xml.rels", _workbook_relationships())
        _write(archive, "xl/styles.xml", _styles())
        _write(
            archive,
            "xl/worksheets/sheet1.xml",
            _sheet_xml(summary_rows, widths=(24, 84), title_row=True),
        )
        _write(
            archive,
            "xl/worksheets/sheet2.xml",
            _sheet_xml(
                data_rows,
                widths=(12, 20, 24, 18, 18, 24, 26, 34, 18, 12, 10, 24, 28, 60),
                freeze_header=True,
                auto_filter=True,
                numeric_columns={8, 10},
            ),
        )
        _write(
            archive,
            "xl/worksheets/sheet3.xml",
            _sheet_xml(notes_rows, widths=(24, 96), freeze_header=True),
        )
    return workbook.getvalue()


def _filter_description(filters: dict[str, Any]) -> str:
    if not filters:
        return "指定なし（既定の全範囲）"
    labels = {
        "country": "国",
        "region": "地域",
        "income_level": "所得区分",
        "indicator": "指標",
        "year_from": "開始年",
        "year_to": "終了年",
        "value_min": "最小値",
        "value_max": "最大値",
        "search": "検索語",
    }
    return " / ".join(f"{labels.get(key, key)}: {value}" for key, value in filters.items())


def _column_description(key: str) -> str:
    descriptions = {
        "country_code": "ISO 3166-1 alpha-3相当の国コード",
        "country_name": "World Bank APIの国名",
        "region": "World Bankの地域区分",
        "income_level": "World Bankの所得区分",
        "category": "資料作成用に付与した指標カテゴリー",
        "indicator_code": "World Bank指標コード",
        "indicator_name": "日本語表示名",
        "indicator_name_en": "World Bank指標の英語名",
        "value": "対象年の指標値",
        "unit": "値の単位",
        "year": "対象年",
        "retrieved_at": "APIから取得した日時",
        "source_name": "データ提供元",
        "source_url": "取得に使用したAPI URL",
    }
    return descriptions.get(key, key)


def _write(archive: ZipFile, path: str, content: str) -> None:
    archive.writestr(path, content.encode("utf-8"))


def _column_name(index: int) -> str:
    value = index + 1
    name = ""
    while value:
        value, remainder = divmod(value - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _cell(reference: str, value: Any, style: int = 0) -> str:
    style_attr = f' s="{style}"' if style else ""
    if isinstance(value, bool):
        return f'<c r="{reference}" t="b"{style_attr}><v>{int(value)}</v></c>'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        numeric = float(value)
        if isfinite(numeric):
            text = str(int(numeric)) if numeric.is_integer() else format(numeric, ".15g")
            return f'<c r="{reference}"{style_attr}><v>{text}</v></c>'
    text = escape(str(value or "")[:32767])
    return (
        f'<c r="{reference}" t="inlineStr"{style_attr}>'
        f'<is><t xml:space="preserve">{text}</t></is></c>'
    )


def _sheet_xml(
    rows: list[list[Any]],
    *,
    widths: tuple[int, ...],
    freeze_header: bool = False,
    auto_filter: bool = False,
    title_row: bool = False,
    numeric_columns: set[int] | None = None,
) -> str:
    numeric_columns = numeric_columns or set()
    max_columns = max((len(row) for row in rows), default=1)
    max_row = max(1, len(rows))
    cols = "".join(
        f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
        for index, width in enumerate(widths, start=1)
    )
    row_xml: list[str] = []
    for row_index, row in enumerate(rows, start=1):
        cells: list[str] = []
        for column_index, value in enumerate(row):
            reference = f"{_column_name(column_index)}{row_index}"
            if title_row and row_index == 1:
                style = 1
            elif row_index == 1 and (freeze_header or auto_filter):
                style = 2
            elif title_row and column_index == 0 and row_index in {3, 4, 5, 6, 8}:
                style = 5
            elif column_index in numeric_columns and row_index > 1:
                style = 3 if column_index == 10 else 4
            else:
                style = 0
            cells.append(_cell(reference, value, style))
        row_height = ' ht="30" customHeight="1"' if title_row and row_index == 1 else ""
        row_xml.append(f'<row r="{row_index}"{row_height}>{"".join(cells)}</row>')

    pane = (
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        if freeze_header
        else ""
    )
    filter_xml = (
        f'<autoFilter ref="A1:{_column_name(max_columns - 1)}{max_row}"/>'
        if auto_filter and rows
        else ""
    )
    merge_xml = '<mergeCells count="1"><mergeCell ref="A1:B1"/></mergeCells>' if title_row else ""
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<dimension ref="A1:{_column_name(max_columns - 1)}{max_row}"/>'
        f'<sheetViews><sheetView workbookViewId="0">{pane}</sheetView></sheetViews>'
        '<sheetFormatPr defaultRowHeight="18"/>'
        f'<cols>{cols}</cols><sheetData>{"".join(row_xml)}</sheetData>'
        f'{filter_xml}{merge_xml}'
        '<pageMargins left="0.3" right="0.3" top="0.5" bottom="0.5" header="0.2" footer="0.2"/>'
        '</worksheet>'
    )


def _content_types() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>'''


def _root_relationships() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>'''


def _workbook() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <bookViews><workbookView xWindow="0" yWindow="0" windowWidth="24000" windowHeight="14000"/></bookViews>
  <sheets>
    <sheet name="Summary" sheetId="1" r:id="rId1"/>
    <sheet name="Data" sheetId="2" r:id="rId2"/>
    <sheet name="Methodology" sheetId="3" r:id="rId3"/>
  </sheets>
  <calcPr calcId="191029"/>
</workbook>'''


def _workbook_relationships() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/>
  <Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>'''


def _styles() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="3">
    <font><sz val="11"/><name val="Aptos"/><family val="2"/></font>
    <font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Aptos"/></font>
    <font><b/><color rgb="FF16324F"/><sz val="18"/><name val="Aptos Display"/></font>
  </fonts>
  <fills count="4">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF176B87"/><bgColor indexed="64"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFE8F3F6"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="2">
    <border><left/><right/><top/><bottom/><diagonal/></border>
    <border><left style="thin"><color rgb="FFD4E1E6"/></left><right style="thin"><color rgb="FFD4E1E6"/></right><top style="thin"><color rgb="FFD4E1E6"/></top><bottom style="thin"><color rgb="FFD4E1E6"/></bottom><diagonal/></border>
  </borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="6">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>
    <xf numFmtId="3" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
    <xf numFmtId="4" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>
    <xf numFmtId="0" fontId="1" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/>
  </cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>'''


def _core_properties(generated_at: str) -> str:
    timestamp = escape(generated_at.replace("+00:00", "Z"))
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>World Data Lens Business Data Export</dc:title>
  <dc:creator>World Data Lens</dc:creator>
  <cp:lastModifiedBy>World Data Lens</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:modified>
</cp:coreProperties>'''


def _app_properties() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>World Data Lens</Application>
  <DocSecurity>0</DocSecurity>
  <ScaleCrop>false</ScaleCrop>
  <HeadingPairs><vt:vector size="2" baseType="variant"><vt:variant><vt:lpstr>Worksheets</vt:lpstr></vt:variant><vt:variant><vt:i4>3</vt:i4></vt:variant></vt:vector></HeadingPairs>
  <TitlesOfParts><vt:vector size="3" baseType="lpstr"><vt:lpstr>Summary</vt:lpstr><vt:lpstr>Data</vt:lpstr><vt:lpstr>Methodology</vt:lpstr></vt:vector></TitlesOfParts>
</Properties>'''
