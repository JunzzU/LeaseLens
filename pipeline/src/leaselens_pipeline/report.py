"""Data-quality report over what is currently loaded, as Markdown."""
from __future__ import annotations

import psycopg


def _table(headers: list[str], rows) -> str:
    out = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    out += ["| " + " | ".join("" if v is None else f"{v:,}" if isinstance(v, int) else str(v) for v in r) + " |"
            for r in rows]
    return "\n".join(out)


def quality_report(conn: psycopg.Connection) -> str:
    q = lambda sql: conn.execute(sql).fetchall()  # noqa: E731
    one = lambda sql: conn.execute(sql).fetchone()  # noqa: E731

    imports = q("""SELECT DISTINCT ON (dataset_name) dataset_name, id, status, source_version,
                          to_char(completed_at, 'YYYY-MM-DD HH24:MI'), record_count, inserted_count,
                          updated_count, unchanged_count, rejected_count
                   FROM data_imports WHERE status <> 'running' ORDER BY dataset_name, id DESC""")
    b = one("""SELECT count(*), count(*) FILTER (WHERE rentsafe_registered),
                      count(*) FILTER (WHERE NOT rentsafe_registered),
                      count(*) FILTER (WHERE geom IS NOT NULL),
                      count(*) FILTER (WHERE storeys IS NULL OR units IS NULL),
                      count(*) FILTER (WHERE postal_fsa IS NULL),
                      count(*) FILTER (WHERE street_number_high > street_number_low)
               FROM buildings""")
    ptypes = q("SELECT coalesce(property_type, '(missing)'), count(*) FROM buildings GROUP BY 1 ORDER BY 2 DESC")
    ev = q("""SELECT scoring_version, count(*), count(DISTINCT building_id), min(evaluation_date),
                     max(evaluation_date), percentile_cont(0.5) WITHIN GROUP (ORDER BY evaluation_score)::int
              FROM evaluations GROUP BY 1 ORDER BY 1""")
    (both,) = one("""SELECT count(*) FROM (SELECT building_id FROM evaluations GROUP BY 1
                                          HAVING count(DISTINCT scoring_version) = 2) x""")
    (never,) = one("""SELECT count(*) FROM buildings b WHERE rentsafe_registered
                      AND NOT EXISTS (SELECT 1 FROM evaluations e WHERE e.building_id = b.id)""")
    (aliases,) = one("SELECT count(*) FROM building_aliases")
    shared = q("""SELECT a.search_text, string_agg(b.source_building_id, ', ' ORDER BY b.source_building_id)
                  FROM building_aliases a JOIN buildings b ON b.id = a.building_id
                  GROUP BY a.normalized_address, a.search_text HAVING count(DISTINCT a.building_id) > 1
                  ORDER BY 1""")
    rejects = q("""SELECT i.dataset_name, r.reason, count(*) FROM import_rejections r
                   JOIN (SELECT DISTINCT ON (dataset_name) id, dataset_name FROM data_imports
                         WHERE status LIKE 'completed%' ORDER BY dataset_name, id DESC) i ON i.id = r.import_id
                   GROUP BY 1, 2 ORDER BY 1, 3 DESC""")
    warnings = q("""SELECT DISTINCT ON (dataset_name) dataset_name, warnings FROM data_imports
                    WHERE status LIKE 'completed%' ORDER BY dataset_name, id DESC""")

    parts = [
        "## Latest import per dataset",
        _table(["Dataset", "Import", "Status", "Source version", "Completed", "Records", "Inserted", "Updated",
                "Unchanged", "Rejected"], imports),
        "## Buildings",
        _table(["Measure", "Count"], [
            ("Buildings", b[0]), ("Registered in RentSafeTO", b[1]),
            ("Evaluated but not in registration (kept, rentsafe_registered = false)", b[2]),
            ("With coordinates", b[3]), ("Missing storeys or units", b[4]), ("Missing postal FSA", b[5]),
            ("Address is a range (e.g. 85-95)", b[6]), ("Registered but never evaluated", never),
            ("Address aliases (one per civic number)", aliases),
        ]),
        _table(["Property type", "Buildings"], ptypes),
        "## Evaluations",
        _table(["Scoring version", "Evaluations", "Buildings", "First", "Latest", "Median score"], ev),
        f"Buildings evaluated under both scoring versions: {both:,}. Their scores are not comparable "
        "across versions, so trends are computed within one version only.",
        "## Rejected rows (latest import)",
        _table(["Dataset", "Reason", "Rows"], rejects) if rejects else "None.",
        "## Warnings (latest import)",
        _table(["Dataset", "Warnings"], [(d, ", ".join(f"{k}: {v}" for k, v in sorted(w.items())) or "none")
                                         for d, w in warnings]),
        "## Addresses shared by more than one building",
        "Search must ask the user to choose between these rather than pick one.",
        _table(["Address", "RSNs"], shared) if shared else "None.",
    ]
    return "\n\n".join(parts) + "\n"
