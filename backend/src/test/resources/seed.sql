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
