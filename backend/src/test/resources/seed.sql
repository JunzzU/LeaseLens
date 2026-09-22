-- Small hand-made dataset covering each search and profile case the tests assert on.
INSERT INTO data_imports (id, dataset_name, source_url, source_version, raw_path, checksum, started_at, completed_at, status)
OVERRIDING SYSTEM VALUE VALUES
  (1, 'registration',        'test', '2026-07-05T09:00:19', 'raw/test', 'x', '2026-09-21 10:00+00', '2026-09-21 10:00+00', 'completed'),
  (2, 'evaluations_pre2023', 'test', '2026-02-20T17:41:23', 'raw/test', 'x', '2026-09-21 10:01+00', '2026-09-21 10:01+00', 'completed'),
  (3, 'evaluations_v2023',   'test', '2026-09-21T09:34:52', 'raw/test', 'x', '2026-09-21 10:02+00', '2026-09-21 10:02+00', 'completed_with_warnings'),
  (4, 'evaluations_v2023',   'test', '2026-09-22T09:00:00', 'raw/test', 'x', '2026-09-22 10:00+00', NULL, 'failed');

INSERT INTO buildings (id, source_building_id, address, street_number_low, street_number_high, street_number_suffix,
                       street_name, street_type, street_direction, normalized_address, postal_fsa, ward, ward_name,
                       latitude, longitude, storeys, units, year_built, year_registered, property_type, rentsafe_registered)
OVERRIDING SYSTEM VALUE VALUES
  (1, '1001', '181-183 GERRARD ST E', 181, 183, '', 'GERRARD', 'ST', 'E', '181|GERRARD|ST|E', 'M5A', '13', 'Toronto Centre', 43.6623, -79.3695, 4, 22, 1930, 2017, 'PRIVATE', true),
  (2, '1002', '123 BLOOR ST W', 123, 123, '', 'BLOOR', 'ST', 'W', '123|BLOOR|ST|W', 'M5S', '11', 'University-Rosedale', 43.668, -79.394, 20, 200, 1968, 2017, 'PRIVATE', true),
  (3, '1003', '123 BLOOR ST E', 123, 123, '', 'BLOOR', 'ST', 'E', '123|BLOOR|ST|E', 'M4W', '13', 'Toronto Centre', 43.671, -79.381, 15, 150, 1970, 2017, 'TCHC', true),
  (4, '1004', '33 FLAMBOROUGH DR', 33, 33, '', 'FLAMBOROUGH', 'DR', '', '33|FLAMBOROUGH|DR|', 'M6M', '05', 'York South-Weston', 43.69, -79.49, 3, 12, 1960, 2017, 'SOCIAL HOUSING', true),
  (5, '1005', '33 FLAMBOROUGH DR', 33, 33, '', 'FLAMBOROUGH', 'DR', '', '33|FLAMBOROUGH|DR|', 'M6M', '05', 'York South-Weston', 43.69, -79.49, 3, 12, 1960, 2017, 'SOCIAL HOUSING', true),
  (6, '1006', '10 NOT REGISTERED RD', 10, 10, '', 'NOT REGISTERED', 'RD', '', '10|NOT REGISTERED|RD|', NULL, '01', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, false);

INSERT INTO building_aliases (building_id, raw_address, normalized_address, search_text, source) VALUES
  (1, '181-183 GERRARD ST E', '181|GERRARD|ST|E', '181 GERRARD ST E', 'registration'),
  (1, '181-183 GERRARD ST E', '183|GERRARD|ST|E', '183 GERRARD ST E', 'registration'),
  (2, '123 BLOOR ST W', '123|BLOOR|ST|W', '123 BLOOR ST W', 'registration'),
  (3, '123 BLOOR ST E', '123|BLOOR|ST|E', '123 BLOOR ST E', 'registration'),
  (4, '33 FLAMBOROUGH DR UNIT B', '33|FLAMBOROUGH|DR|', '33 FLAMBOROUGH DR', 'registration'),
  (5, '33 FLAMBOROUGH DR UNIT C', '33|FLAMBOROUGH|DR|', '33 FLAMBOROUGH DR', 'registration'),
  (6, '10 NOT REGISTERED RD', '10|NOT REGISTERED|RD|', '10 NOT REGISTERED RD', 'evaluations_v2023');

INSERT INTO evaluations (building_id, scoring_version, evaluation_date, evaluation_score, proactive_score,
                         areas_evaluated, result_text, raw_payload, created_import_id, updated_import_id) VALUES
  (1, 'PRE_2023', '2022-01-10', 70, NULL, 18, 'Evaluation needs to be conducted in 2 years', '{}', 2, 2),
  (1, 'V2023',    '2024-03-08', 78, 78, 45, NULL, '{}', 3, 3),
  (1, 'V2023',    '2026-06-12', 84, 84, 45, NULL, '{}', 3, 3),
  (2, 'PRE_2023', '2021-05-01', 88, NULL, 20, 'Evaluation needs to be conducted in 3 years', '{}', 2, 2),
  (2, 'V2023',    '2025-02-02', 93, 93, 47, NULL, '{}', 3, 3);

INSERT INTO data_imports (id, dataset_name, source_url, source_version, raw_path, checksum, started_at, completed_at, status)
OVERRIDING SYSTEM VALUE VALUES
  (5, 'permits_active',  'test', '2026-09-21T10:25:31', 'raw/test', 'x', '2026-09-21 10:03+00', '2026-09-21 10:03+00', 'completed'),
  (6, 'permits_cleared', 'test', '2026-09-21T11:19:35', 'raw/test', 'x', '2026-09-21 10:04+00', '2026-09-21 10:04+00', 'completed');

INSERT INTO permits (id, permit_number, revision_number, permit_type, source_file, status, structure_type, work,
                     work_category, description, application_date, issued_date, completed_date, est_const_cost,
                     street_num, street_name, street_type, street_direction, raw_payload, created_import_id, updated_import_id)
OVERRIDING SYSTEM VALUE VALUES
  (1, '26 100001 BLD', '00', 'Building Additions/Alterations', 'ACTIVE', 'Inspection', 'Apartment Building',
   'Balcony/Guard Repairs', 'ALTERATION_OR_REPAIR', 'Balcony slab repairs', '2026-04-01', '2026-06-12', NULL, 25000.00,
   '183', 'GERRARD', 'ST', 'E', '{}', 5, 5),
  (2, '24 100002 PLB', '00', 'Plumbing(PS)', 'CLEARED', 'Closed', 'Apartment Building',
   'Building Permit Related(PS)', 'ALTERATION_OR_REPAIR', 'Plumbing - suite alterations', '2024-01-10', '2024-02-01', '2024-09-30', NULL,
   '181', 'GERRARD', 'ST', 'E', '{}', 6, 6),
  (3, '25 100003 NEW', '00', 'New Building', 'ACTIVE', 'Permit Issued', 'Apartment Building',
   'New Building', 'NEW_CONSTRUCTION', 'Construct a new 30 storey rental building on the site', '2025-05-05', NULL, NULL, 90000000.00,
   '181-183', 'GERRARD', 'ST', 'E', '{}', 5, 5),
  (4, '99 100004 DEM', '00', 'Demolition Folder (DM)', 'CLEARED', 'Closed', 'SFD - Detached',
   'Demolition', 'DEMOLITION', 'Demolish house', '1920-01-01', NULL, '2017-05-01', NULL,
   '181', 'GERRARD', 'ST', 'E', '{}', 6, 6),
  (5, '25 100005 BLD', '00', 'Building Additions/Alterations', 'ACTIVE', 'Inspection', 'Apartment Building',
   'Other(BA)', 'ALTERATION_OR_REPAIR', 'Shared-address permit', '2025-07-07', '2025-08-08', NULL, NULL,
   '33', 'FLAMBOROUGH', 'DR', '', '{}', 5, 5);

INSERT INTO permit_matches (permit_id, building_id, match_method, match_confidence, site_relation, accepted,
                            source_address, target_address, import_id) VALUES
  (1, 1, 'ADDRESS', 'HIGH', 'BUILDING', true, '183 GERRARD ST E', '183 GERRARD ST E', 5),
  (2, 1, 'ADDRESS', 'HIGH', 'BUILDING', true, '181 GERRARD ST E', '181 GERRARD ST E', 6),
  (3, 1, 'PERMIT_RANGE', 'MEDIUM', 'BUILDING', true, '181-183 GERRARD ST E', '181 GERRARD ST E', 5),
  (4, 1, 'ADDRESS', 'MEDIUM', 'OTHER_STRUCTURE_ON_SITE', true, '181 GERRARD ST E', '181 GERRARD ST E', 6),
  (5, 4, 'ADDRESS', 'LOW', 'BUILDING', false, '33 FLAMBOROUGH DR', '33 FLAMBOROUGH DR', 5),
  (5, 5, 'ADDRESS', 'LOW', 'BUILDING', false, '33 FLAMBOROUGH DR', '33 FLAMBOROUGH DR', 5);

-- 20 comparison peers for building 1 (ward 13, 22 units, 4 storeys, latest V2023 score 84 on 2026-06-12):
-- same ward, 20-24 units, 4 storeys, V2023 scores 70..89 within the 2-year window.
INSERT INTO buildings (id, source_building_id, address, street_number_low, street_number_high, street_name,
                       street_type, normalized_address, ward, ward_name, latitude, longitude, storeys, units,
                       year_built, property_type, rentsafe_registered)
OVERRIDING SYSTEM VALUE
SELECT 100 + n, (2000 + n)::text, (100 + n) || ' PEER ST', 100 + n, 100 + n, 'PEER', 'ST', (100 + n) || '|PEER|ST|',
       '13', 'Toronto Centre', 43.66, -79.37, 4, 20 + n % 5, 1960,
       CASE WHEN n < 17 THEN 'PRIVATE' ELSE 'TCHC' END, true
FROM generate_series(0, 19) AS n;

INSERT INTO evaluations (building_id, scoring_version, evaluation_date, evaluation_score, raw_payload,
                         created_import_id, updated_import_id)
SELECT 100 + n, 'V2023', DATE '2025-06-01' + n, 70 + n, '{}', 3, 3 FROM generate_series(0, 19) AS n;

-- A size-matched building whose only evaluation is outside the window: excluded, and counted as such.
INSERT INTO buildings (id, source_building_id, address, street_number_low, street_number_high, street_name,
                       street_type, normalized_address, ward, storeys, units, rentsafe_registered)
OVERRIDING SYSTEM VALUE VALUES (200, '3000', '1 OLD ST', 1, 1, 'OLD', 'ST', '1|OLD|ST|', '13', 4, 22, true);
INSERT INTO evaluations (building_id, scoring_version, evaluation_date, evaluation_score, raw_payload,
                         created_import_id, updated_import_id)
VALUES (200, 'V2023', '2023-07-01', 50, '{}', 3, 3);
