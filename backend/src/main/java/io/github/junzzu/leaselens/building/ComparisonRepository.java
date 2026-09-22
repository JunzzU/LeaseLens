package io.github.junzzu.leaselens.building;

import io.github.junzzu.leaselens.building.Comparison.PeerRule;
import io.github.junzzu.leaselens.building.Comparison.Score;
import io.github.junzzu.leaselens.building.Comparison.Spread;
import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

@Repository
public class ComparisonRepository {

    /** Latest 2023+ evaluation per building; older-method scores are never compared. */
    private static final String LATEST = """
            WITH latest AS (
                SELECT DISTINCT ON (building_id) building_id, evaluation_date AS d, evaluation_score AS s
                FROM evaluations
                WHERE scoring_version = 'V2023' AND evaluation_score IS NOT NULL
                ORDER BY building_id, evaluation_date DESC)
            """;

    /** Buildings passing a rule's size/location test; {@code recent} = usable latest evaluation. */
    private static final String CANDIDATES = LATEST + """
            , t AS (SELECT b.id, b.ward, b.units, b.storeys, b.geom, l.d, l.s
                    FROM buildings b JOIN latest l ON l.building_id = b.id WHERE b.id = :id)
            , recent_permits AS (
                SELECT m.building_id, count(*) AS n
                FROM permit_matches m JOIN permits p ON p.id = m.permit_id
                WHERE m.accepted AND p.application_date >= :since
                GROUP BY m.building_id)
            , candidates AS (
                SELECT b.id, b.property_type, l.s, coalesce(rp.n, 0) AS permits,
                       (l.d IS NOT NULL AND abs(l.d - t.d) <= :window) AS recent
                FROM buildings b
                CROSS JOIN t
                LEFT JOIN latest l ON l.building_id = b.id
                LEFT JOIN recent_permits rp ON rp.building_id = b.id
                WHERE b.id <> t.id AND b.units IS NOT NULL AND b.storeys IS NOT NULL
                  AND (NOT :sameWard OR b.ward = t.ward)
                  AND (CAST(:radius AS integer) IS NULL
                       OR (b.geom IS NOT NULL AND ST_DWithin(b.geom, t.geom, :radius)))
                  AND b.units BETWEEN t.units * (1 - :unitsPct / 100.0) AND t.units * (1 + :unitsPct / 100.0)
                  AND abs(b.storeys - t.storeys) <= :storeys)
            """;

    private final JdbcClient jdbc;

    public ComparisonRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public Optional<Score> latestCurrentScore(long buildingId) {
        return jdbc.sql(LATEST + "SELECT s, d FROM latest WHERE building_id = :id")
                .param("id", buildingId)
                .query((rs, i) -> new Score(rs.getInt("s"), rs.getObject("d", LocalDate.class)))
                .optional();
    }

    public int recentPermitCount(long buildingId, LocalDate since) {
        return jdbc.sql("""
                        SELECT count(*) FROM permit_matches m JOIN permits p ON p.id = m.permit_id
                        WHERE m.building_id = :id AND m.accepted AND p.application_date >= :since""")
                .param("id", buildingId).param("since", since).query(Integer.class).single();
    }

    public record PeerCounts(int usable, int excluded) {}

    public PeerCounts count(long buildingId, PeerRule rule, LocalDate since) {
        return bind(jdbc.sql(CANDIDATES + """
                        SELECT count(*) FILTER (WHERE recent) AS usable, count(*) FILTER (WHERE NOT recent) AS excluded
                        FROM candidates"""), buildingId, rule, since)
                .query((rs, i) -> new PeerCounts(rs.getInt("usable"), rs.getInt("excluded")))
                .single();
    }

    public record PeerStats(Spread spread, int percentBelow, int percentEqual, double permitMedian,
                            double permitUpperQuartile) {}

    public PeerStats stats(long buildingId, PeerRule rule, LocalDate since) {
        return bind(jdbc.sql(CANDIDATES + """
                        SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY c.s) AS median,
                               percentile_cont(0.25) WITHIN GROUP (ORDER BY c.s) AS q1,
                               percentile_cont(0.75) WITHIN GROUP (ORDER BY c.s) AS q3,
                               min(c.s) AS min, max(c.s) AS max,
                               round(100.0 * count(*) FILTER (WHERE c.s < t.s) / count(*))::int AS below,
                               round(100.0 * count(*) FILTER (WHERE c.s = t.s) / count(*))::int AS equal,
                               percentile_cont(0.5) WITHIN GROUP (ORDER BY c.permits) AS permit_median,
                               percentile_cont(0.75) WITHIN GROUP (ORDER BY c.permits) AS permit_q3
                        FROM candidates c CROSS JOIN t
                        WHERE c.recent"""), buildingId, rule, since)
                .query((rs, i) -> new PeerStats(
                        new Spread(rs.getDouble("median"), rs.getDouble("q1"), rs.getDouble("q3"),
                                rs.getInt("min"), rs.getInt("max")),
                        rs.getInt("below"), rs.getInt("equal"), rs.getDouble("permit_median"),
                        rs.getDouble("permit_q3")))
                .single();
    }

    public Map<String, Integer> propertyTypes(long buildingId, PeerRule rule, LocalDate since) {
        Map<String, Integer> types = new LinkedHashMap<>();
        bind(jdbc.sql(CANDIDATES + """
                        SELECT coalesce(property_type, 'UNKNOWN') AS type, count(*) AS n FROM candidates
                        WHERE recent GROUP BY 1 ORDER BY 2 DESC, 1"""), buildingId, rule, since)
                .query((rs, i) -> types.put(rs.getString("type"), rs.getInt("n")))
                .list();
        return types;
    }

    private static JdbcClient.StatementSpec bind(JdbcClient.StatementSpec sql, long id, PeerRule rule, LocalDate since) {
        return sql.param("id", id)
                .param("since", since)
                .param("window", Comparison.EVALUATION_WINDOW_DAYS)
                .param("sameWard", rule.sameWard)
                .param("radius", rule.radiusMetres)
                .param("unitsPct", rule.unitsWithinPercent)
                .param("storeys", rule.storeysWithin);
    }
}
