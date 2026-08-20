PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS indicator_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    country_code TEXT NOT NULL,
    country_name TEXT NOT NULL,
    region TEXT NOT NULL,
    income_level TEXT NOT NULL,
    indicator_code TEXT NOT NULL,
    indicator_name TEXT NOT NULL,
    unit TEXT NOT NULL,
    value REAL NOT NULL,
    year INTEGER NOT NULL,
    period TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    UNIQUE(country_code, indicator_code, year)
);

CREATE INDEX IF NOT EXISTS idx_indicator_values_indicator_year
    ON indicator_values(indicator_code, year);
CREATE INDEX IF NOT EXISTS idx_indicator_values_region
    ON indicator_values(region);
CREATE INDEX IF NOT EXISTS idx_indicator_values_country
    ON indicator_values(country_code);

CREATE TABLE IF NOT EXISTS update_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL CHECK(status IN ('running', 'success', 'partial', 'failed')),
    fetched_count INTEGER NOT NULL DEFAULT 0,
    inserted_count INTEGER NOT NULL DEFAULT 0,
    updated_count INTEGER NOT NULL DEFAULT 0,
    unchanged_count INTEGER NOT NULL DEFAULT 0,
    skipped_count INTEGER NOT NULL DEFAULT 0,
    failure_count INTEGER NOT NULL DEFAULT 0,
    message TEXT NOT NULL DEFAULT ''
);
