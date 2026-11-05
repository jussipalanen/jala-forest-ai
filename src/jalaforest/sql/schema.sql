-- Idempotent schema. Table names are unqualified so tests can run the same
-- DDL in an isolated schema via search_path.
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS import_runs (
    run_id          bigserial PRIMARY KEY,
    source          text        NOT NULL,
    request_url     text,
    bbox            text        NOT NULL,
    started_at      timestamptz NOT NULL,
    fetched_at      timestamptz,
    status          text        NOT NULL CHECK (status IN ('success', 'failed')),
    expected_count  integer,
    feature_count   integer,
    content_sha256  text,
    error           text
);

-- Latest successful import per source: the data currently in the tables.
CREATE OR REPLACE VIEW current_source_versions AS
SELECT DISTINCT ON (source)
       source, run_id, fetched_at, feature_count, content_sha256, request_url
FROM import_runs
WHERE status = 'success'
ORDER BY source, run_id DESC;

CREATE TABLE IF NOT EXISTS forest_stands (
    stand_id        bigint PRIMARY KEY,
    feature_id      text   NOT NULL UNIQUE,
    source          text   NOT NULL,
    source_area_ha  double precision,
    attributes      jsonb  NOT NULL,
    geom            geometry(MultiPolygon, 3067) NOT NULL
);
CREATE INDEX IF NOT EXISTS forest_stands_geom_idx ON forest_stands USING gist (geom);

CREATE TABLE IF NOT EXISTS natura_sites (
    feature_id      text PRIMARY KEY,
    source          text NOT NULL,
    site_code       text NOT NULL,
    site_name       text,
    site_type       text,
    attributes      jsonb NOT NULL,
    geom            geometry(MultiPolygon, 3067) NOT NULL
);
CREATE INDEX IF NOT EXISTS natura_sites_geom_idx ON natura_sites USING gist (geom);
CREATE INDEX IF NOT EXISTS natura_sites_source_idx ON natura_sites (source);
