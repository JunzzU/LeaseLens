-- LeaseLens Toronto: core schema (Week 2).
-- Flyway-style file name so the Spring Boot backend can take over migrations in Week 3.
-- Tables for permits, neighbourhoods, users and watchlists arrive in later migrations.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- One row per run of the pipeline against one source file.
CREATE TABLE data_imports (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dataset_name    text        NOT NULL,             -- e.g. 'evaluations_v2023'
    source_url      text        NOT NULL,
    source_version  text,                             -- portal last_modified for the resource
    raw_path        text        NOT NULL,             -- raw/<dataset>/<date>/source.csv
    checksum        text        NOT NULL,             -- sha256 of the raw file
    source_columns  text[],                           -- header of the raw file, to detect schema drift
    started_at      timestamptz NOT NULL DEFAULT now(),
    completed_at    timestamptz,
    status          text        NOT NULL DEFAULT 'running'
                    CHECK (status IN ('running', 'completed', 'completed_with_warnings', 'failed')),
    record_count    integer,
    inserted_count  integer,
    updated_count   integer,
    unchanged_count integer,
    rejected_count  integer,
    warnings        jsonb       NOT NULL DEFAULT '{}'::jsonb,   -- counts by warning type, schema drift
    error_summary   text
);
CREATE INDEX data_imports_dataset_idx ON data_imports (dataset_name, started_at DESC);

-- Source rows the pipeline refused to load, kept so every rejection is explainable.
CREATE TABLE import_rejections (
    id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    import_id   bigint  NOT NULL REFERENCES data_imports (id) ON DELETE CASCADE,
    source_row  integer NOT NULL,       -- 1-based data row in the raw file
    reason      text    NOT NULL,
    raw_payload jsonb   NOT NULL
);
CREATE INDEX import_rejections_import_idx ON import_rejections (import_id);

-- Canonical building. For RentSafeTO buildings source_building_id is the RSN.
CREATE TABLE buildings (
    id                   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_building_id   text    NOT NULL UNIQUE,
    address              text    NOT NULL,          -- display form, e.g. '181-183 GERRARD ST E'
    street_number_low    integer NOT NULL,
    street_number_high   integer NOT NULL,
    street_number_suffix text    NOT NULL DEFAULT '',
    street_name          text    NOT NULL,
    street_type          text    NOT NULL DEFAULT '',
    street_direction     text    NOT NULL DEFAULT '',
    normalized_address   text    NOT NULL,          -- key of the first civic number
    postal_fsa           char(3),
    ward                 text,
    ward_name            text,
    latitude             double precision,
    longitude            double precision,
    geom                 geography(Point, 4326),
    storeys              integer CHECK (storeys > 0),
    units                integer CHECK (units > 0),
    year_built           integer,
    year_registered      integer,
    property_type        text,                      -- PRIVATE | TCHC | SOCIAL HOUSING
    rentsafe_registered  boolean NOT NULL,
    registration_payload jsonb,                     -- latest registration row, untouched
    created_import_id    bigint  REFERENCES data_imports (id),
    updated_import_id    bigint  REFERENCES data_imports (id),
    created_at           timestamptz NOT NULL DEFAULT now(),
    updated_at           timestamptz NOT NULL DEFAULT now(),
    CHECK (street_number_high >= street_number_low),
    CHECK ((latitude IS NULL) = (longitude IS NULL))
);
CREATE INDEX buildings_normalized_address_idx ON buildings (normalized_address);
CREATE INDEX buildings_geom_idx ON buildings USING gist (geom);
CREATE INDEX buildings_ward_idx ON buildings (ward);

-- Every address a building is known by: each number of a range, historical spellings.
CREATE TABLE building_aliases (
    id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    building_id        bigint NOT NULL REFERENCES buildings (id) ON DELETE CASCADE,
    raw_address        text   NOT NULL,
    normalized_address text   NOT NULL,
    search_text        text   NOT NULL,     -- '181 GERRARD ST E', for prefix/fuzzy search
    source             text   NOT NULL,     -- dataset that supplied it
    UNIQUE (building_id, normalized_address)
);
CREATE INDEX building_aliases_normalized_idx ON building_aliases (normalized_address);
CREATE INDEX building_aliases_search_trgm_idx ON building_aliases USING gin (search_text gin_trgm_ops);

-- RentSafeTO evaluations. Scores from different scoring versions are not comparable
-- (see docs/data-audit.md, finding 1): trends and percentiles stay within one version.
CREATE TABLE evaluations (
    id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    building_id        bigint  NOT NULL REFERENCES buildings (id) ON DELETE CASCADE,
    scoring_version    text    NOT NULL CHECK (scoring_version IN ('PRE_2023', 'V2023')),
    evaluation_date    date    NOT NULL,
    evaluation_score   integer CHECK (evaluation_score BETWEEN 0 AND 100),
    proactive_score    integer CHECK (proactive_score BETWEEN 0 AND 100),   -- V2023 only
    areas_evaluated    integer,
    result_text        text,                                              -- PRE_2023 only
    latitude           double precision,  -- where the City located the building at that time;
    longitude          double precision,  -- the only coordinates RentSafeTO publishes
    ward_name          text,
    source_record_id   text,             -- portal _id; informational, not a stable key
    raw_payload        jsonb   NOT NULL,
    created_import_id  bigint  NOT NULL REFERENCES data_imports (id),
    updated_import_id  bigint  NOT NULL REFERENCES data_imports (id),
    created_at         timestamptz NOT NULL DEFAULT now(),
    updated_at         timestamptz NOT NULL DEFAULT now(),
    UNIQUE (building_id, evaluation_date, scoring_version)
);
CREATE INDEX evaluations_building_idx ON evaluations (building_id, evaluation_date DESC);

-- What changed in each import; feeds the timeline and watchlist notifications.
CREATE TABLE building_changes (
    id             bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    building_id    bigint NOT NULL REFERENCES buildings (id) ON DELETE CASCADE,
    entity_type    text   NOT NULL,        -- building | evaluation | permit
    entity_id      bigint NOT NULL,
    change_type    text   NOT NULL,        -- e.g. new_evaluation, evaluation_changed, deregistered
    change_summary text   NOT NULL,
    detected_at    timestamptz NOT NULL DEFAULT now(),
    import_id      bigint NOT NULL REFERENCES data_imports (id)
);
CREATE INDEX building_changes_building_idx ON building_changes (building_id, detected_at DESC);
