package io.github.junzzu.leaselens.building;

import io.github.junzzu.leaselens.building.EvaluationRecord.ScoringVersion;
import io.github.junzzu.leaselens.building.PermitRecord.Listing;
import io.github.junzzu.leaselens.building.PermitRecord.WorkCategory;
import io.github.junzzu.leaselens.building.TimelineEvent.DatePrecision;
import io.github.junzzu.leaselens.building.TimelineEvent.Type;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDate;
import java.util.List;
import java.util.Set;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/**
 * Evaluations and attached permits merged into one dated list. A permit contributes up to three
 * events (applied, issued, closed), matching how a renter would see it unfold.
 *
 * <p>Registration year is deliberately not an event: the City's YEAR_REGISTERED is often later than
 * the building's first evaluation (e.g. 2023 for a building evaluated in 2017), so it is not the
 * year the building joined RentSafeTO.
 */
@Repository
public class TimelineRepository {

    /** Date the City's current evaluation method started (first V2023 evaluation citywide was 2023-06-05). */
    static final LocalDate SCORING_CHANGE = LocalDate.of(2023, 6, 1);

    private static final String EVENTS = """
            WITH b AS (SELECT id, year_built FROM buildings WHERE id = :id),
            attached AS (
                SELECT p.*, m.site_relation,
                       (p.application_date IS NOT NULL AND b.year_built IS NOT NULL
                        AND extract(year FROM p.application_date) < b.year_built) AS predates
                FROM permits p
                JOIN permit_matches m ON m.permit_id = p.id AND m.accepted
                JOIN b ON b.id = m.building_id),
            events AS (
                SELECT e.evaluation_date AS date, 'DAY' AS precision, 'EVALUATION' AS type,
                       CASE e.scoring_version WHEN 'V2023' THEN 'evaluations_v2023' ELSE 'evaluations_pre2023' END
                           AS source,
                       e.evaluation_score AS score, e.scoring_version, NULL::bigint AS permit_id, 1 AS rank
                FROM evaluations e JOIN b ON b.id = e.building_id
              UNION ALL
                SELECT application_date, 'DAY', 'PERMIT_APPLIED', lower('permits_' || source_file), NULL, NULL, id, 4
                FROM attached WHERE application_date IS NOT NULL
              UNION ALL
                SELECT issued_date, 'DAY', 'PERMIT_ISSUED', lower('permits_' || source_file), NULL, NULL, id, 3
                FROM attached WHERE issued_date IS NOT NULL
              UNION ALL
                SELECT completed_date, 'DAY', 'PERMIT_CLOSED', lower('permits_' || source_file), NULL, NULL, id, 2
                FROM attached WHERE completed_date IS NOT NULL
              UNION ALL
                SELECT :scoringChange, 'MONTH', 'SCORING_SYSTEM_CHANGE', 'evaluations_v2023', NULL, NULL, NULL, 5
                WHERE (SELECT count(DISTINCT scoring_version) FROM evaluations e JOIN b ON b.id = e.building_id) = 2
            )
            """;

    private final JdbcClient jdbc;

    public TimelineRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    public int count(long buildingId, Set<Type> types) {
        return jdbc.sql(EVENTS + "SELECT count(*) FROM events WHERE type = ANY(:types)")
                .param("id", buildingId).param("scoringChange", SCORING_CHANGE).param("types", names(types))
                .query(Integer.class).single();
    }

    /** Newest first; on the same day, a permit's closing sorts above its issue above its application. */
    public List<TimelineEvent> find(long buildingId, Set<Type> types, int limit, int offset) {
        return jdbc.sql(EVENTS + """
                        SELECT ev.*, a.permit_number, a.permit_type, a.status, a.source_file, a.work_category,
                               a.site_relation, a.description, a.predates
                        FROM events ev LEFT JOIN attached a ON a.id = ev.permit_id
                        WHERE ev.type = ANY(:types)
                        ORDER BY ev.date DESC, ev.rank, a.permit_number, a.permit_type
                        LIMIT :limit OFFSET :offset""")
                .param("id", buildingId).param("scoringChange", SCORING_CHANGE).param("types", names(types))
                .param("limit", limit).param("offset", offset)
                .query((rs, i) -> event(rs))
                .list();
    }

    private static String[] names(Set<Type> types) {
        return types.stream().map(Enum::name).toArray(String[]::new);
    }

    private static TimelineEvent event(ResultSet rs) throws SQLException {
        Type type = Type.valueOf(rs.getString("type"));
        TimelineEvent.Evaluation evaluation = null;
        TimelineEvent.Permit permit = null;
        if (type == Type.EVALUATION) {
            int score = rs.getInt("score");
            evaluation = new TimelineEvent.Evaluation(rs.wasNull() ? null : score,
                    ScoringVersion.valueOf(rs.getString("scoring_version")));
        } else if (rs.getString("permit_number") != null) {
            permit = new TimelineEvent.Permit(rs.getString("permit_number"), rs.getString("permit_type"),
                    rs.getString("status"), Listing.valueOf(rs.getString("source_file")),
                    WorkCategory.valueOf(rs.getString("work_category")), rs.getString("site_relation"),
                    rs.getString("description"), rs.getBoolean("predates"));
        }
        return new TimelineEvent(rs.getObject("date", LocalDate.class),
                DatePrecision.valueOf(rs.getString("precision")), type, rs.getString("source"), evaluation, permit);
    }
}
