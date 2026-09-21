-- Search-as-you-type: "123 BLO" becomes the pattern '123|BLO%' on the alias key.
-- text_pattern_ops lets LIKE 'prefix%' use a B-tree index regardless of collation.
CREATE INDEX building_aliases_prefix_idx ON building_aliases (normalized_address text_pattern_ops);
