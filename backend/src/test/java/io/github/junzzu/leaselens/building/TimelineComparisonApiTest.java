package io.github.junzzu.leaselens.building;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.flyway.autoconfigure.FlywayMigrationStrategy;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;
import org.springframework.http.HttpStatus;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.test.context.jdbc.SqlConfig;
import org.springframework.test.web.servlet.assertj.MockMvcTester;

/** Timeline, comparison and data-source endpoints against the seeded test database. */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Sql(scripts = "/seed.sql", config = @SqlConfig(transactionMode = SqlConfig.TransactionMode.ISOLATED))
@Sql(statements = "TRUNCATE data_imports, buildings RESTART IDENTITY CASCADE",
        executionPhase = Sql.ExecutionPhase.AFTER_TEST_METHOD)
class TimelineComparisonApiTest {

    @TestConfiguration
    static class Config {
        @Bean
        FlywayMigrationStrategy cleanThenMigrate() {
            return (Flyway flyway) -> {
                flyway.clean();
                flyway.migrate();
            };
        }

        /** "Today" is fixed so "last 5 years" and "days since import" are deterministic. */
        @Bean
        @Primary
        Clock fixedClock() {
            return Clock.fixed(Instant.parse("2026-09-22T12:00:00Z"), ZoneOffset.UTC);
        }
    }

    @Autowired
    MockMvcTester mvc;

    @Test
    void timelineMergesEvaluationsAndPermitMilestonesNewestFirst() {
        assertThat(mvc.get().uri("/api/v1/buildings/1/timeline")).hasStatusOk().bodyJson()
                .hasPathSatisfying("$.total", v -> v.assertThat().isEqualTo(12))
                .hasPathSatisfying("$.events[*].type", v -> v.assertThat().asList().containsExactly(
                        "EVALUATION", "PERMIT_ISSUED", "PERMIT_APPLIED", "PERMIT_APPLIED", "PERMIT_CLOSED",
                        "EVALUATION", "PERMIT_ISSUED", "PERMIT_APPLIED", "SCORING_SYSTEM_CHANGE", "EVALUATION",
                        "PERMIT_CLOSED", "PERMIT_APPLIED"))
                .hasPathSatisfying("$.events[0].date", v -> v.assertThat().isEqualTo("2026-06-12"))
                .hasPathSatisfying("$.events[0].evaluation.score", v -> v.assertThat().isEqualTo(84))
                .hasPathSatisfying("$.events[1].permit.permitNumber", v -> v.assertThat().isEqualTo("26 100001 BLD"))
                .hasPathSatisfying("$.events[8].datePrecision", v -> v.assertThat().isEqualTo("MONTH"))
                .hasPathSatisfying("$.events[11].permit.predatesBuilding", v -> v.assertThat().isEqualTo(true));
    }

    @Test
    void timelineFiltersAndPages() {
        assertThat(mvc.get().uri("/api/v1/buildings/1/timeline?types=EVALUATION")).bodyJson()
                .hasPathSatisfying("$.total", v -> v.assertThat().isEqualTo(3))
                .hasPathSatisfying("$.events[*].type", v -> v.assertThat().asList().containsOnly("EVALUATION"));
        assertThat(mvc.get().uri("/api/v1/buildings/1/timeline?limit=2&offset=2")).bodyJson()
                .hasPathSatisfying("$.total", v -> v.assertThat().isEqualTo(12))
                .hasPathSatisfying("$.events[*].date", v -> v.assertThat().asList()
                        .containsExactly("2026-04-01", "2025-05-05"));
        assertThat(mvc.get().uri("/api/v1/buildings/1/timeline?types=BOGUS")).hasStatus(HttpStatus.BAD_REQUEST);
    }

    @Test
    void timelineLeavesOutPermitsThatAreNotAttached() {
        assertThat(mvc.get().uri("/api/v1/buildings/4/timeline")).bodyJson()
                .hasPathSatisfying("$.total", v -> v.assertThat().isEqualTo(0));
        assertThat(mvc.get().uri("/api/v1/buildings/999/timeline")).hasStatus(HttpStatus.NOT_FOUND);
    }

    @Test
    void comparisonUsesTheFirstRuleWithEnoughPeers() {
        assertThat(mvc.get().uri("/api/v1/buildings/1/comparison")).hasStatusOk().bodyJson()
                .hasPathSatisfying("$.availability", v -> v.assertThat().isEqualTo("AVAILABLE"))
                .hasPathSatisfying("$.rule.code", v -> v.assertThat().isEqualTo("SAME_WARD_SIMILAR_SIZE"))
                .hasPathSatisfying("$.rule.unitsWithinPercent", v -> v.assertThat().isEqualTo(25))
                .hasPathSatisfying("$.rule.evaluationWindowDays", v -> v.assertThat().isEqualTo(730))
                .hasPathSatisfying("$.peerCount", v -> v.assertThat().isEqualTo(20))
                .hasPathSatisfying("$.target.score", v -> v.assertThat().isEqualTo(84))
                .hasPathSatisfying("$.peerScores.median", v -> v.assertThat().isEqualTo(79.5))
                .hasPathSatisfying("$.peerScores.min", v -> v.assertThat().isEqualTo(70))
                .hasPathSatisfying("$.percentOfPeersBelow", v -> v.assertThat().isEqualTo(70))
                .hasPathSatisfying("$.percentOfPeersEqual", v -> v.assertThat().isEqualTo(5))
                .hasPathSatisfying("$.excludedWithoutRecentEvaluation", v -> v.assertThat().isEqualTo(1))
                .hasPathSatisfying("$.peerPropertyTypes.PRIVATE", v -> v.assertThat().isEqualTo(17))
                .hasPathSatisfying("$.peerPropertyTypes.TCHC", v -> v.assertThat().isEqualTo(3));
    }

    @Test
    void comparisonCountsRecentPermitsOnly() {
        // Building 1 has permits applied 2026, 2025 and 2024 (counted) and 1920 (not).
        assertThat(mvc.get().uri("/api/v1/buildings/1/comparison")).bodyJson()
                .hasPathSatisfying("$.permitActivity.building", v -> v.assertThat().isEqualTo(3))
                .hasPathSatisfying("$.permitActivity.peerMedian", v -> v.assertThat().isEqualTo(0.0));
    }

    @Test
    void comparisonWithholdsThePercentileForSmallGroups() {
        // Building 2: 200 units in ward 11, nobody similar under any rule.
        assertThat(mvc.get().uri("/api/v1/buildings/2/comparison")).bodyJson()
                .hasPathSatisfying("$.availability", v -> v.assertThat().isEqualTo("TOO_FEW_PEERS"))
                .hasPathSatisfying("$.rule.code", v -> v.assertThat().isEqualTo("WITHIN_3_KM_BROADER_SIZE"))
                .hasPathSatisfying("$.target.score", v -> v.assertThat().isEqualTo(93))
                .hasPathSatisfying("$.percentOfPeersBelow", v -> v.assertThat().isNull())
                .hasPathSatisfying("$.peerScores", v -> v.assertThat().isNull());
    }

    @Test
    void comparisonExplainsWhyItIsUnavailable() {
        assertThat(mvc.get().uri("/api/v1/buildings/4/comparison")).bodyJson()
                .hasPathSatisfying("$.availability", v -> v.assertThat().isEqualTo("NO_CURRENT_EVALUATION"))
                .hasPathSatisfying("$.rule", v -> v.assertThat().isNull());
        assertThat(mvc.get().uri("/api/v1/buildings/6/comparison")).bodyJson()
                .hasPathSatisfying("$.availability", v -> v.assertThat().isEqualTo("MISSING_BUILDING_SIZE"));
        assertThat(mvc.get().uri("/api/v1/buildings/999/comparison")).hasStatus(HttpStatus.NOT_FOUND);
    }

    @Test
    void dataSourcesShowLastSuccessAndLastAttemptSeparately() {
        assertThat(mvc.get().uri("/api/v1/data-sources/status")).hasStatusOk().bodyJson()
                .hasPathSatisfying("$.datasets.length()", v -> v.assertThat().isEqualTo(5))
                .hasPathSatisfying("$.datasets[?(@.dataset == 'evaluations_v2023')].lastSuccessfulImport.sourceVersion",
                        v -> v.assertThat().asList().containsExactly("2026-09-21T09:34:52"))
                .hasPathSatisfying("$.datasets[?(@.dataset == 'evaluations_v2023')].lastAttempt.status",
                        v -> v.assertThat().asList().containsExactly("failed"))
                .hasPathSatisfying("$.datasets[?(@.dataset == 'registration')].daysSinceSuccessfulImport",
                        v -> v.assertThat().asList().containsExactly(1))
                .hasPathSatisfying("$.datasets[?(@.dataset == 'evaluations_pre2023')].updatedByCity",
                        v -> v.assertThat().asList().containsExactly(false))
                .hasPathSatisfying("$.licence", v -> v.assertThat().asString().contains("Open Government Licence"));
    }

    @Test
    void failureDetailsAreNotExposed() {
        assertThat(mvc.get().uri("/api/v1/data-sources/status")).body().asString().doesNotContain("error");
    }
}
