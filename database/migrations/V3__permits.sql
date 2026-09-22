-- Building permits (Week 4). Only permits whose address matches a RentSafeTO building
-- are stored; the raw files keep everything else. See docs/matching-methodology.md.

-- Street as one string ("THE WEST MALL", "BLOOR ST") so it compares equal whichever way a
-- source split name and type: the City's permit records say name 'THE WEST MALL', type ''.
ALTER TABLE building_aliases ADD COLUMN match_key text GENERATED ALWAYS AS (
    split_part(normalized_address, '|', 1) || '|' ||
    btrim(split_part(normalized_address, '|', 2) || ' ' || split_part(normalized_address, '|', 3)) || '|' ||
    split_part(normalized_address, '|', 4)
) STORED;
CREATE INDEX building_aliases_match_key_idx ON building_aliases (match_key);

-- Rows in a source that were valid but not loaded (e.g. permits for other properties).
ALTER TABLE data_imports ADD COLUMN skipped_count integer;

CREATE TABLE permits (
    id                     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    permit_number          text NOT NULL,
    revision_number        text NOT NULL,         -- zero-padded to 2 digits
    permit_type            text NOT NULL,
    source_file            text NOT NULL CHECK (source_file IN ('ACTIVE', 'CLEARED')),
    status                 text,
    structure_type         text,
    work                   text,
    -- Derived from permit_type/work/description: is this new construction or demolition on
    -- the site, rather than work on the existing building? (docs/matching-methodology.md)
    work_category          text NOT NULL CHECK (work_category IN ('NEW_CONSTRUCTION', 'DEMOLITION',
                                                                  'ALTERATION_OR_REPAIR')),
    description            text,
    current_use            text,
    proposed_use           text,
    application_date       date,
    issued_date            date,
    completed_date         date,                  -- CLEARED only
    est_const_cost         numeric(14, 2),        -- null when the field holds text
    dwelling_units_created integer,
    dwelling_units_lost    integer,
    street_num             text,                  -- as published: '273-275', '58 A'
    street_name            text,
    street_type            text,
    street_direction       text,
    postal_fsa             text,
    geo_id                 text,
    raw_payload            jsonb  NOT NULL,       -- source row minus _id and BUILDER_NAME (personal names)
    created_import_id      bigint NOT NULL REFERENCES data_imports (id),
    updated_import_id      bigint NOT NULL REFERENCES data_imports (id),
    created_at             timestamptz NOT NULL DEFAULT now(),
    updated_at             timestamptz NOT NULL DEFAULT now(),
    UNIQUE (permit_number, revision_number, permit_type)   -- audit finding 4
);

-- Why a permit is attached to a building. One row per candidate building.
CREATE TABLE permit_matches (
    permit_id        bigint NOT NULL REFERENCES permits (id) ON DELETE CASCADE,
    building_id      bigint NOT NULL REFERENCES buildings (id) ON DELETE CASCADE,
    match_method     text   NOT NULL CHECK (match_method IN ('ADDRESS', 'PERMIT_RANGE')),
    match_confidence text   NOT NULL CHECK (match_confidence IN ('HIGH', 'MEDIUM', 'LOW')),
    site_relation    text   NOT NULL CHECK (site_relation IN ('BUILDING', 'NON_RESIDENTIAL_SPACE',
                                                              'OTHER_STRUCTURE_ON_SITE')),
    -- false when the address belongs to more than one building: never attach silently
    accepted         boolean NOT NULL,
    source_address   text   NOT NULL,   -- permit address as published
    target_address   text   NOT NULL,   -- building alias it matched
    distance_metres  double precision,  -- reserved for coordinate-based matching
    matched_at       timestamptz NOT NULL DEFAULT now(),
    import_id        bigint NOT NULL REFERENCES data_imports (id),
    PRIMARY KEY (permit_id, building_id)
);
CREATE INDEX permit_matches_building_idx ON permit_matches (building_id) WHERE accepted;
