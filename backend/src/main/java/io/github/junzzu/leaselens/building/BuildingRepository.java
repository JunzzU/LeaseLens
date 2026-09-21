package io.github.junzzu.leaselens.building;

import io.github.junzzu.leaselens.building.BuildingSummary.Location;
import io.github.junzzu.leaselens.building.BuildingSummary.SourceFreshness;
import io.github.junzzu.leaselens.building.SearchResponse.Result;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

/** Read-only queries over the tables the pipeline loads. All SQL is parameterized. */
@Repository
public class BuildingRepository {

    private static final RowMapper<Result> RESULT = (rs, i) -> new Result(
            rs.getLong("id"), rs.getString("source_building_id"), rs.getString("address"),
            rs.getString("matched_address"), rs.getString("ward_name"), integer(rs, "storeys"),
            integer(rs, "units"), rs.getBoolean("rentsafe_registered"));

    /** One row per building (its best-matching alias), in street then number order. */
    private static final String SEARCH = """
            SELECT id, source_building_id, address, matched_address, ward_name, storeys, units,
                   rentsafe_registered FROM (
                SELECT DISTINCT ON (b.id) b.id, b.source_building_id, b.address, a.search_text AS matched_address,
                       b.ward_name, b.storeys, b.units, b.rentsafe_registered, b.street_name,
                       b.street_number_low, %s AS rank
                FROM building_aliases a JOIN buildings b ON b.id = a.building_id
                WHERE %s
                ORDER BY b.id, %s
            ) x
            ORDER BY %s
            LIMIT :limit
            """;

    private final JdbcClient jdbc;

    public BuildingRepository(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    /** {@code pattern} is a LIKE pattern on the alias key, e.g. {@code 123|BLOOR|%|W}. */
    public List<Result> searchByKeyPattern(String pattern, int limit) {
        String sql = SEARCH.formatted("0", "a.normalized_address LIKE :pattern ESCAPE '\\'",
                "a.normalized_address", "street_name, street_number_low, id");
        return jdbc.sql(sql).param("pattern", pattern).param("limit", limit).query(RESULT).list();
    }

    /** Buildings on streets containing {@code street}, which must already be LIKE-escaped. */
    public List<Result> searchByStreet(String street, int limit) {
        String sql = SEARCH.formatted("0", "a.search_text LIKE '% ' || :street || '%' ESCAPE '\\'",
                "a.normalized_address", "street_name, street_number_low, id");
        return jdbc.sql(sql).param("street", street).param("limit", limit).query(RESULT).list();
    }

    /** Similar-looking addresses (pg_trgm), most similar first. */
    public List<Result> searchFuzzy(String text, int limit) {
        String sql = SEARCH.formatted("similarity(a.search_text, :text)", "a.search_text % :text",
                "similarity(a.search_text, :text) DESC", "rank DESC, id");
        return jdbc.sql(sql).param("text", text).param("limit", limit).query(RESULT).list();
    }

    public Optional<BuildingRow> findBuilding(long id) {
        return jdbc.sql("""
                        SELECT id, source_building_id, address, postal_fsa, ward, ward_name, latitude, longitude,
                               storeys, units, year_built, year_registered, property_type, rentsafe_registered
                        FROM buildings WHERE id = :id""")
                .param("id", id)
                .query((rs, i) -> new BuildingRow(
                        rs.getLong("id"), rs.getString("source_building_id"), rs.getString("address"),
                        rs.getString("postal_fsa"), rs.getString("ward"), rs.getString("ward_name"),
                        location(rs), integer(rs, "storeys"), integer(rs, "units"), integer(rs, "year_built"),
                        integer(rs, "year_registered"), rs.getString("property_type"),
                        rs.getBoolean("rentsafe_registered")))
                .optional();
    }

    public List<String> findAliases(long buildingId) {
        return jdbc.sql("SELECT search_text FROM building_aliases WHERE building_id = :id ORDER BY normalized_address")
                .param("id", buildingId).query(String.class).list();
    }

    public boolean sharesAddressWithAnotherBuilding(long buildingId) {
        return jdbc.sql("""
                        SELECT EXISTS (SELECT 1 FROM building_aliases mine
                                       JOIN building_aliases other
                                         ON other.normalized_address = mine.normalized_address
                                        AND other.building_id <> mine.building_id
                                       WHERE mine.building_id = :id)""")
                .param("id", buildingId).query(Boolean.class).single();
    }

    /** All evaluations, newest first. */
    public List<EvaluationRecord> findEvaluations(long buildingId) {
        return jdbc.sql("""
                        SELECT evaluation_date, scoring_version, evaluation_score, proactive_score,
                               areas_evaluated, result_text, i.completed_at AS imported_at
                        FROM evaluations e JOIN data_imports i ON i.id = e.updated_import_id
                        WHERE building_id = :id
                        ORDER BY evaluation_date DESC, scoring_version DESC""")
                .param("id", buildingId)
                .query((rs, i) -> new EvaluationRecord(
                        rs.getObject("evaluation_date", LocalDate.class),
                        EvaluationRecord.ScoringVersion.valueOf(rs.getString("scoring_version")),
                        integer(rs, "evaluation_score"), integer(rs, "proactive_score"),
                        integer(rs, "areas_evaluated"), rs.getString("result_text"),
                        rs.getObject("imported_at", OffsetDateTime.class)))
                .list();
    }

    /** Latest successful import of each dataset a building profile draws on. */
    public List<SourceFreshness> findSourceFreshness() {
        return jdbc.sql("""
                        SELECT DISTINCT ON (dataset_name) dataset_name, completed_at, source_version
                        FROM data_imports
                        WHERE status LIKE 'completed%' AND dataset_name IN
                              ('registration', 'evaluations_pre2023', 'evaluations_v2023')
                        ORDER BY dataset_name, id DESC""")
                .query((rs, i) -> new SourceFreshness(rs.getString("dataset_name"),
                        rs.getObject("completed_at", OffsetDateTime.class), rs.getString("source_version")))
                .list();
    }

    private static Location location(ResultSet rs) throws SQLException {
        double lat = rs.getDouble("latitude");
        return rs.wasNull() ? null : new Location(lat, rs.getDouble("longitude"));
    }

    private static Integer integer(ResultSet rs, String column) throws SQLException {
        int v = rs.getInt(column);
        return rs.wasNull() ? null : v;
    }

    public record BuildingRow(long id, String rsn, String address, String postalFsa, String ward, String wardName,
                              Location location, Integer storeys, Integer units, Integer yearBuilt,
                              Integer yearRegistered, String propertyType, boolean rentSafeRegistered) {}
}
