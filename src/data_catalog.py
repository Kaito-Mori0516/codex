"""Curated country and indicator catalog shared by local and AWS runtimes.

The default scope intentionally favors indicators that are repeatedly used in
market briefs, country comparisons, board papers, and presentation decks.  It
is broad enough to be useful without downloading every World Bank series.
"""

from __future__ import annotations

from typing import Any


INDICATORS: dict[str, dict[str, Any]] = {
    "NY.GDP.MKTP.CD": {
        "name": "GDP (current US$)",
        "display_name": "名目GDP",
        "short_name": "GDP",
        "unit": "US$",
        "category": "経済",
        "description": "国内で生産された財・サービスの市場価値（名目、米ドル換算）",
        "decimals": 0,
    },
    "NY.GDP.PCAP.CD": {
        "name": "GDP per capita (current US$)",
        "display_name": "1人当たりGDP",
        "short_name": "GDP per capita",
        "unit": "US$",
        "category": "経済",
        "description": "名目GDPを人口で除した1人当たりの経済規模",
        "decimals": 0,
    },
    "NY.GDP.MKTP.KD.ZG": {
        "name": "GDP growth (annual %)",
        "display_name": "実質GDP成長率",
        "short_name": "GDP growth",
        "unit": "%",
        "category": "経済",
        "description": "物価変動の影響を除いたGDPの前年比成長率",
        "decimals": 2,
    },
    "FP.CPI.TOTL.ZG": {
        "name": "Inflation, consumer prices (annual %)",
        "display_name": "消費者物価上昇率",
        "short_name": "Inflation",
        "unit": "%",
        "category": "経済",
        "description": "消費者物価指数で測る年間インフレ率",
        "decimals": 2,
    },
    "SL.UEM.TOTL.ZS": {
        "name": "Unemployment, total (% of total labor force)",
        "display_name": "失業率",
        "short_name": "Unemployment",
        "unit": "%",
        "category": "雇用",
        "description": "労働力人口に占める失業者の割合（ILO推計）",
        "decimals": 2,
    },
    "NE.EXP.GNFS.ZS": {
        "name": "Exports of goods and services (% of GDP)",
        "display_name": "輸出比率（GDP比）",
        "short_name": "Exports / GDP",
        "unit": "%",
        "category": "貿易",
        "description": "財・サービス輸出額がGDPに占める割合",
        "decimals": 2,
    },
    "SP.POP.TOTL": {
        "name": "Population, total",
        "display_name": "人口（総数）",
        "short_name": "Population",
        "unit": "人",
        "category": "人口・社会",
        "description": "年央時点の推計人口",
        "decimals": 0,
    },
    "SP.URB.TOTL.IN.ZS": {
        "name": "Urban population (% of total population)",
        "display_name": "都市人口比率",
        "short_name": "Urban population",
        "unit": "%",
        "category": "人口・社会",
        "description": "総人口に占める都市居住人口の割合",
        "decimals": 2,
    },
    "SP.DYN.LE00.IN": {
        "name": "Life expectancy at birth, total (years)",
        "display_name": "平均寿命",
        "short_name": "Life expectancy",
        "unit": "年",
        "category": "人口・社会",
        "description": "出生時点で期待される平均生存年数",
        "decimals": 2,
    },
    "IT.NET.USER.ZS": {
        "name": "Individuals using the Internet (% of population)",
        "display_name": "インターネット利用率",
        "short_name": "Internet use",
        "unit": "%",
        "category": "デジタル",
        "description": "過去3か月以内にインターネットを利用した人口割合",
        "decimals": 2,
    },
    "EN.ATM.CO2E.PC": {
        "name": "CO2 emissions (metric tons per capita)",
        "display_name": "1人当たりCO2排出量",
        "short_name": "CO2 per capita",
        "unit": "t/人",
        "category": "環境・エネルギー",
        "description": "化石燃料燃焼等による1人当たり二酸化炭素排出量",
        "decimals": 2,
    },
    "EG.FEC.RNEW.ZS": {
        "name": "Renewable energy consumption (% of total final energy consumption)",
        "display_name": "再生可能エネルギー比率",
        "short_name": "Renewable energy",
        "unit": "%",
        "category": "環境・エネルギー",
        "description": "最終エネルギー消費に占める再生可能エネルギーの割合",
        "decimals": 2,
    },
}


COUNTRIES: dict[str, dict[str, str]] = {
    "JPN": {"name_ja": "日本", "name_en": "Japan", "group": "アジア・太平洋"},
    "KOR": {"name_ja": "韓国", "name_en": "Korea, Rep.", "group": "アジア・太平洋"},
    "CHN": {"name_ja": "中国", "name_en": "China", "group": "アジア・太平洋"},
    "HKG": {"name_ja": "香港", "name_en": "Hong Kong SAR, China", "group": "アジア・太平洋"},
    "SGP": {"name_ja": "シンガポール", "name_en": "Singapore", "group": "アジア・太平洋"},
    "IND": {"name_ja": "インド", "name_en": "India", "group": "アジア・太平洋"},
    "IDN": {"name_ja": "インドネシア", "name_en": "Indonesia", "group": "アジア・太平洋"},
    "THA": {"name_ja": "タイ", "name_en": "Thailand", "group": "アジア・太平洋"},
    "VNM": {"name_ja": "ベトナム", "name_en": "Viet Nam", "group": "アジア・太平洋"},
    "PHL": {"name_ja": "フィリピン", "name_en": "Philippines", "group": "アジア・太平洋"},
    "AUS": {"name_ja": "オーストラリア", "name_en": "Australia", "group": "アジア・太平洋"},
    "NZL": {"name_ja": "ニュージーランド", "name_en": "New Zealand", "group": "アジア・太平洋"},
    "USA": {"name_ja": "米国", "name_en": "United States", "group": "北米"},
    "CAN": {"name_ja": "カナダ", "name_en": "Canada", "group": "北米"},
    "MEX": {"name_ja": "メキシコ", "name_en": "Mexico", "group": "中南米"},
    "BRA": {"name_ja": "ブラジル", "name_en": "Brazil", "group": "中南米"},
    "ARG": {"name_ja": "アルゼンチン", "name_en": "Argentina", "group": "中南米"},
    "CHL": {"name_ja": "チリ", "name_en": "Chile", "group": "中南米"},
    "GBR": {"name_ja": "英国", "name_en": "United Kingdom", "group": "欧州"},
    "FRA": {"name_ja": "フランス", "name_en": "France", "group": "欧州"},
    "DEU": {"name_ja": "ドイツ", "name_en": "Germany", "group": "欧州"},
    "ITA": {"name_ja": "イタリア", "name_en": "Italy", "group": "欧州"},
    "ESP": {"name_ja": "スペイン", "name_en": "Spain", "group": "欧州"},
    "NLD": {"name_ja": "オランダ", "name_en": "Netherlands", "group": "欧州"},
    "CHE": {"name_ja": "スイス", "name_en": "Switzerland", "group": "欧州"},
    "SWE": {"name_ja": "スウェーデン", "name_en": "Sweden", "group": "欧州"},
    "NOR": {"name_ja": "ノルウェー", "name_en": "Norway", "group": "欧州"},
    "POL": {"name_ja": "ポーランド", "name_en": "Poland", "group": "欧州"},
    "TUR": {"name_ja": "トルコ", "name_en": "Turkiye", "group": "欧州・中東"},
    "SAU": {"name_ja": "サウジアラビア", "name_en": "Saudi Arabia", "group": "中東・アフリカ"},
    "ARE": {"name_ja": "アラブ首長国連邦", "name_en": "United Arab Emirates", "group": "中東・アフリカ"},
    "ISR": {"name_ja": "イスラエル", "name_en": "Israel", "group": "中東・アフリカ"},
    "ZAF": {"name_ja": "南アフリカ", "name_en": "South Africa", "group": "中東・アフリカ"},
    "NGA": {"name_ja": "ナイジェリア", "name_en": "Nigeria", "group": "中東・アフリカ"},
    "EGY": {"name_ja": "エジプト", "name_en": "Egypt, Arab Rep.", "group": "中東・アフリカ"},
}


DEFAULT_COUNTRIES = tuple(COUNTRIES)


def public_catalog(country_codes: tuple[str, ...] | None = None) -> dict[str, Any]:
    """Return JSON-safe catalog metadata for browsers and export workbooks."""

    selected = country_codes or DEFAULT_COUNTRIES
    return {
        "countries": [
            {"country_code": code, **COUNTRIES.get(code, {"name_ja": code, "name_en": code, "group": "その他"})}
            for code in selected
        ],
        "indicators": [
            {"indicator_code": code, **metadata}
            for code, metadata in INDICATORS.items()
        ],
        "categories": list(dict.fromkeys(item["category"] for item in INDICATORS.values())),
    }
