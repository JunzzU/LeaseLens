package io.github.junzzu.leaselens.datasource;

import io.github.junzzu.leaselens.datasource.DataSourceStatus.Attempt;
import io.github.junzzu.leaselens.datasource.DataSourceStatus.Dataset;
import io.github.junzzu.leaselens.datasource.DataSourceStatus.Import;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.time.Clock;
import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/data-sources")
@Tag(name = "Data sources")
public class DataSourceController {

    private record Known(String dataset, String title, String portalPackage, boolean updatedByCity) {}

    private static final List<Known> DATASETS = List.of(
            new Known("registration", "Apartment Building Registration", "apartment-building-registration", true),
            new Known("evaluations_v2023", "Apartment Building Evaluations (2023 – current)",
                    "apartment-building-evaluation", true),
            new Known("evaluations_pre2023", "Apartment Building Evaluations (pre-2023)",
                    "apartment-building-evaluation", false),
            new Known("permits_active", "Building Permits – Active Permits", "building-permits-active-permits", true),
            new Known("permits_cleared", "Building Permits – Cleared Permits (since 2017)",
                    "building-permits-cleared-permits", true));

    private final JdbcClient jdbc;
    private final Clock clock;

    public DataSourceController(JdbcClient jdbc, Clock clock) {
        this.jdbc = jdbc;
        this.clock = clock;
    }

    @GetMapping("/status")
    @Operation(summary = "Each dataset's source, last successful import and last attempt")
    public DataSourceStatus status() {
        OffsetDateTime now = OffsetDateTime.now(clock);
        List<Dataset> datasets = DATASETS.stream().map(k -> {
            Optional<Import> ok = jdbc.sql("""
                            SELECT completed_at, source_version, record_count FROM data_imports
                            WHERE dataset_name = :d AND status LIKE 'completed%' ORDER BY id DESC LIMIT 1""")
                    .param("d", k.dataset())
                    .query((rs, i) -> new Import(rs.getObject("completed_at", OffsetDateTime.class),
                            rs.getString("source_version"), (Integer) rs.getObject("record_count")))
                    .optional();
            // Status only: error details stay in the database, not in a public API.
            Optional<Attempt> last = jdbc.sql("""
                            SELECT started_at, status FROM data_imports WHERE dataset_name = :d
                            ORDER BY id DESC LIMIT 1""")
                    .param("d", k.dataset())
                    .query((rs, i) -> new Attempt(rs.getObject("started_at", OffsetDateTime.class),
                            rs.getString("status")))
                    .optional();
            Integer days = ok.map(i -> (int) Duration.between(i.importedAt(), now).toDays()).orElse(null);
            return new Dataset(k.dataset(), k.title(), "https://open.toronto.ca/dataset/" + k.portalPackage() + "/",
                    k.updatedByCity(), ok.orElse(null), last.orElse(null), days);
        }).toList();
        return new DataSourceStatus(datasets, DataSourceStatus.LICENCE);
    }
}
