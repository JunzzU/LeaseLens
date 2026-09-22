package io.github.junzzu.leaselens.building;

import io.github.junzzu.leaselens.building.BuildingSummary.PermitSummary;
import io.github.junzzu.leaselens.building.PermitRecord.Listing;
import io.github.junzzu.leaselens.building.PermitRecord.Match;
import io.github.junzzu.leaselens.building.PermitRecord.WorkCategory;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** Permits attached to a building. Only accepted (unambiguous) matches are ever returned. */
@Repository
public class PermitRepository {

    private static final String ATTACHED = """
            FROM permits p
            JOIN permit_matches m ON m.permit_id = p.id AND m.accepted
            JOIN buildings b ON b.id = m.building_id
            WHERE m.building_id = :id
            """;

    private final JdbcClient jdbc;

    public PermitRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /** Newest activity first: issued date, else application date. {@code listing} null means both. */
    public List<PermitRecord> find(long buildingId, Listing listing, int limit, int offset) {
        return jdbc.sql("""
                        SELECT p.*, m.match_method, m.match_confidence, m.site_relation, m.source_address,
                               b.year_built, i.completed_at AS imported_at
                        FROM permits p
                        JOIN permit_matches m ON m.permit_id = p.id AND m.accepted
                        JOIN buildings b ON b.id = m.building_id
                        JOIN data_imports i ON i.id = p.updated_import_id
                        WHERE m.building_id = :id
                          AND (CAST(:listing AS text) IS NULL OR p.source_file = :listing)
                        ORDER BY coalesce(p.issued_date, p.application_date) DESC NULLS LAST,
                                 p.permit_number, p.revision_number, p.permit_type
                        LIMIT :limit OFFSET :offset""")
                .param("id", buildingId)
                .param("listing", listing == null ? null : listing.name())
                .param("limit", limit)
                .param("offset", offset)
                .query((rs, i) -> record(rs))
                .list();
    }

    public PermitSummary summarize(long buildingId) {
        return jdbc.sql("""
                        SELECT count(*) FILTER (WHERE p.source_file = 'ACTIVE') AS active,
                               count(*) FILTER (WHERE p.source_file = 'CLEARED') AS cleared,
                               count(*) FILTER (WHERE p.source_file = 'ACTIVE'
                                                AND p.work_category <> 'ALTERATION_OR_REPAIR') AS active_site_work,
                               max(coalesce(p.issued_date, p.application_date)) AS latest
                        """ + ATTACHED)
                .param("id", buildingId)
                .query((rs, i) -> new PermitSummary(rs.getInt("active"), rs.getInt("cleared"),
                        rs.getInt("active_site_work"), rs.getObject("latest", LocalDate.class)))
                .single();
    }

    /** Permits at this building's address that we did not attach because another building shares it. */
    public boolean hasUnattachedSharedAddressPermits(long buildingId) {
        return jdbc.sql("SELECT EXISTS (SELECT 1 FROM permit_matches WHERE building_id = :id AND NOT accepted)")
                .param("id", buildingId).query(Boolean.class).single();
    }

    private static PermitRecord record(ResultSet rs) throws SQLException {
        LocalDate applied = rs.getObject("application_date", LocalDate.class);
        int yearBuilt = rs.getInt("year_built");
        boolean predates = !rs.wasNull() && applied != null && applied.getYear() < yearBuilt;
        return new PermitRecord(
                rs.getString("permit_number"), rs.getString("revision_number"), rs.getString("permit_type"),
                Listing.valueOf(rs.getString("source_file")), rs.getString("status"),
                WorkCategory.valueOf(rs.getString("work_category")), rs.getString("work"),
                rs.getString("structure_type"), rs.getString("description"), applied,
                rs.getObject("issued_date", LocalDate.class), rs.getObject("completed_date", LocalDate.class),
                rs.getBigDecimal("est_const_cost"), integer(rs, "dwelling_units_created"),
                integer(rs, "dwelling_units_lost"), predates,
                new Match(rs.getString("match_method"), rs.getString("match_confidence"),
                        rs.getString("site_relation"), rs.getString("source_address")),
                rs.getObject("imported_at", OffsetDateTime.class));
    }

    private static Integer integer(ResultSet rs, String column) throws SQLException {
        int v = rs.getInt(column);
        return rs.wasNull() ? null : v;
    }
}
