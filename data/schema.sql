CREATE TABLE IF NOT EXISTS rtt (
    provider_code TEXT,
    specialty TEXT,
    weeks REAL,
    as_of TEXT,
    PRIMARY KEY (provider_code, specialty, as_of)
);

CREATE TABLE IF NOT EXISTS planned_care (
    region TEXT,
    provider TEXT,
    specialty TEXT,
    source_url TEXT,
    metric TEXT,
    average_wait_weeks REAL,
    patients_seen_within_weeks REAL,
    page_last_updated TEXT
);

CREATE TABLE IF NOT EXISTS identity (
    provider_code TEXT PRIMARY KEY,
    provider_name TEXT,
    cqc_provider_id TEXT
);
