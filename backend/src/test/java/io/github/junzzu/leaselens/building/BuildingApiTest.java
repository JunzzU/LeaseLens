package io.github.junzzu.leaselens.building;

import static org.assertj.core.api.Assertions.assertThat;

import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.flyway.autoconfigure.FlywayMigrationStrategy;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.annotation.Bean;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.jdbc.Sql;
import org.springframework.test.context.jdbc.SqlConfig;
import org.springframework.test.web.servlet.assertj.MockMvcTester;
import org.springframework.test.web.servlet.assertj.MvcTestResult;

/** HTTP-level tests against a real PostgreSQL + PostGIS database (leaselens_api_test). */
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Sql(scripts = "/seed.sql", config = @SqlConfig(transactionMode = SqlConfig.TransactionMode.ISOLATED))
@Sql(statements = "TRUNCATE data_imports, buildings RESTART IDENTITY CASCADE",
        executionPhase = Sql.ExecutionPhase.AFTER_TEST_METHOD)
class BuildingApiTest {

    @TestConfiguration
    static class FreshSchema {
        /** Rebuild the schema from the migrations, exactly as production would create it. */
        @Bean
        FlywayMigrationStrategy cleanThenMigrate() {
            return (Flyway flyway) -> {
                flyway.clean();
                flyway.migrate();
            };
        }
    }

    @Autowired
    MockMvcTester mvc;

    private MvcTestResult search(String q) {
        return mvc.get().uri("/api/v1/buildings/search").param("q", q).exchange();
    }

    @Test
    void fullAddressInAnySpellingFindsTheBuilding() {
        for (String q : new String[] {"181 Gerrard Street East", "181 GERRARD ST E", "181 gerrard st. e."}) {
            assertThat(search(q)).hasStatusOk().bodyJson()
                    .hasPathSatisfying("$.matchType", v -> v.assertThat().isEqualTo("ADDRESS"))
                    .hasPathSatisfying("$.ambiguous", v -> v.assertThat().isEqualTo(false))
                    .hasPathSatisfying("$.results[0].buildingId", v -> v.assertThat().isEqualTo(1))
                    .hasPathSatisfying("$.results[0].matchedAddress", v -> v.assertThat().isEqualTo("181 GERRARD ST E"));
        }
    }

    @Test
    void anyNumberInARangeFindsTheBuilding() {
        assertThat(search("183 gerrard st e")).bodyJson()
                .hasPathSatisfying("$.results[0].address", v -> v.assertThat().isEqualTo("181-183 GERRARD ST E"))
                .hasPathSatisfying("$.results[0].matchedAddress", v -> v.assertThat().isEqualTo("183 GERRARD ST E"));
    }

    @Test
    void leavingOutTheDirectionReturnsEveryCandidate() {
        assertThat(search("123 bloor")).bodyJson()
                .hasPathSatisfying("$.matchType", v -> v.assertThat().isEqualTo("ADDRESS"))
                .hasPathSatisfying("$.ambiguous", v -> v.assertThat().isEqualTo(true))
                .hasPathSatisfying("$.results.length()", v -> v.assertThat().isEqualTo(2));
        assertThat(search("123 bloor st w")).bodyJson()
                .hasPathSatisfying("$.results.length()", v -> v.assertThat().isEqualTo(1))
                .hasPathSatisfying("$.results[0].buildingId", v -> v.assertThat().isEqualTo(2));
    }

    @Test
    void buildingsSharingAnAddressAreBothReturned() {
        assertThat(search("33 flamborough dr")).bodyJson()
                .hasPathSatisfying("$.ambiguous", v -> v.assertThat().isEqualTo(true))
                .hasPathSatisfying("$.results[*].buildingId", v -> v.assertThat().asList().containsExactlyInAnyOrder(4, 5))
                .hasPathSatisfying("$.results[*].rsn", v -> v.assertThat().asList().containsExactlyInAnyOrder("1004", "1005"))
                .hasPathSatisfying("$.results[0].units", v -> v.assertThat().isEqualTo(12));
    }

    @Test
    void partialInputIsAPrefixMatch() {
        assertThat(search("123 blo")).bodyJson()
                .hasPathSatisfying("$.matchType", v -> v.assertThat().isEqualTo("PREFIX"))
                .hasPathSatisfying("$.results.length()", v -> v.assertThat().isEqualTo(2));
    }

    @Test
    void streetWithoutNumberListsBuildingsOnThatStreet() {
        assertThat(search("Gerrard Street East")).bodyJson()
                .hasPathSatisfying("$.matchType", v -> v.assertThat().isEqualTo("STREET"))
                .hasPathSatisfying("$.results[0].buildingId", v -> v.assertThat().isEqualTo(1));
    }

    @Test
    void typoFallsBackToFuzzyAndSaysSo() {
        assertThat(search("181 gerard st e")).bodyJson()
                .hasPathSatisfying("$.matchType", v -> v.assertThat().isEqualTo("FUZZY"))
                .hasPathSatisfying("$.results[0].buildingId", v -> v.assertThat().isEqualTo(1));
    }

    @Test
    void noMatchIsAnEmptyListNotAnError() {
        assertThat(search("zzzz qqqq")).hasStatusOk().bodyJson()
                .hasPathSatisfying("$.matchType", v -> v.assertThat().isEqualTo("NONE"))
                .hasPathSatisfying("$.results.length()", v -> v.assertThat().isEqualTo(0));
    }

    @Test
    void wildcardsInTheQueryAreNotInterpreted() {
        assertThat(search("1% _ '")).hasStatusOk().bodyJson()
                .hasPathSatisfying("$.results.length()", v -> v.assertThat().isEqualTo(0));
    }

    @Test
    void invalidQueriesAreProblemDetails() {
        assertThat(search(" ")).hasStatus(HttpStatus.BAD_REQUEST)
                .hasContentTypeCompatibleWith(MediaType.APPLICATION_PROBLEM_JSON)
                .bodyJson().hasPathSatisfying("$.detail", v -> v.assertThat().asString().contains("q"));
        assertThat(search("1".repeat(101))).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(mvc.get().uri("/api/v1/buildings/search?q=bloor&limit=0")).hasStatus(HttpStatus.BAD_REQUEST);
    }

    @Test
    void profileComparesOnlyWithinOneScoringVersion() {
        assertThat(mvc.get().uri("/api/v1/buildings/1")).hasStatusOk().bodyJson()
                .hasPathSatisfying("$.rsn", v -> v.assertThat().isEqualTo("1001"))
                .hasPathSatisfying("$.knownAddresses", v -> v.assertThat().asList()
                        .containsExactly("181 GERRARD ST E", "183 GERRARD ST E"))
                .hasPathSatisfying("$.location.latitude", v -> v.assertThat().isEqualTo(43.6623))
                .hasPathSatisfying("$.evaluations.count", v -> v.assertThat().isEqualTo(3))
                .hasPathSatisfying("$.evaluations.countByScoringVersion.PRE_2023", v -> v.assertThat().isEqualTo(1))
                .hasPathSatisfying("$.evaluations.latest.score", v -> v.assertThat().isEqualTo(84))
                .hasPathSatisfying("$.evaluations.previous.date", v -> v.assertThat().isEqualTo("2024-03-08"))
                .hasPathSatisfying("$.evaluations.changeFromPrevious", v -> v.assertThat().isEqualTo(6))
                .hasPathSatisfying("$.coverageNotes", v -> v.assertThat().asList()
                        .containsExactly("BUILDING_NOT_UNIT", "SCORING_SYSTEM_CHANGED"));
    }

    @Test
    void profileShowsFreshnessOfTheLatestSuccessfulImportOnly() {
        assertThat(mvc.get().uri("/api/v1/buildings/1")).bodyJson()
                .hasPathSatisfying("$.sources.length()", v -> v.assertThat().isEqualTo(5))
                .hasPathSatisfying("$.sources[?(@.dataset == 'evaluations_v2023')].sourceVersion",
                        v -> v.assertThat().asList().containsExactly("2026-09-21T09:34:52"));
    }

    @Test
    void profileOfSparseBuildingExplainsWhatIsMissing() {
        assertThat(mvc.get().uri("/api/v1/buildings/6")).hasStatusOk().bodyJson()
                .hasPathSatisfying("$.rentSafeRegistered", v -> v.assertThat().isEqualTo(false))
                .hasPathSatisfying("$.location", v -> v.assertThat().isNull())
                .hasPathSatisfying("$.evaluations.latest", v -> v.assertThat().isNull())
                .hasPathSatisfying("$.evaluations.changeFromPrevious", v -> v.assertThat().isNull())
                .hasPathSatisfying("$.coverageNotes", v -> v.assertThat().asList().containsExactly(
                        "BUILDING_NOT_UNIT", "NOT_IN_CURRENT_REGISTRATION", "NO_EVALUATIONS", "NO_LOCATION"));
    }

    @Test
    void profileFlagsSharedAddresses() {
        assertThat(mvc.get().uri("/api/v1/buildings/4")).bodyJson()
                .hasPathSatisfying("$.coverageNotes", v -> v.assertThat().asList()
                        .contains("ADDRESS_SHARED_WITH_OTHER_BUILDING"));
    }

    @Test
    void profileSummarizesAttachedPermits() {
        assertThat(mvc.get().uri("/api/v1/buildings/1")).bodyJson()
                .hasPathSatisfying("$.permits.active", v -> v.assertThat().isEqualTo(2))
                .hasPathSatisfying("$.permits.cleared", v -> v.assertThat().isEqualTo(2))
                .hasPathSatisfying("$.permits.activeNewConstructionOrDemolition", v -> v.assertThat().isEqualTo(1))
                .hasPathSatisfying("$.permits.latestActivity", v -> v.assertThat().isEqualTo("2026-06-12"));
    }

    @Test
    void permitsNewestFirstWithMatchEvidence() {
        assertThat(mvc.get().uri("/api/v1/buildings/1/permits")).hasStatusOk().bodyJson()
                .hasPathSatisfying("$.total", v -> v.assertThat().isEqualTo(4))
                .hasPathSatisfying("$.permits[*].permitNumber", v -> v.assertThat().asList().containsExactly(
                        "26 100001 BLD", "25 100003 NEW", "24 100002 PLB", "99 100004 DEM"))
                .hasPathSatisfying("$.permits[0].match.method", v -> v.assertThat().isEqualTo("ADDRESS"))
                .hasPathSatisfying("$.permits[0].match.permitAddress", v -> v.assertThat().isEqualTo("183 GERRARD ST E"))
                .hasPathSatisfying("$.permits[0].estimatedCost", v -> v.assertThat().isEqualTo(25000.00))
                .hasPathSatisfying("$.permits[1].workCategory", v -> v.assertThat().isEqualTo("NEW_CONSTRUCTION"))
                .hasPathSatisfying("$.permits[1].match.confidence", v -> v.assertThat().isEqualTo("MEDIUM"))
                .hasPathSatisfying("$.permits[3].predatesBuilding", v -> v.assertThat().isEqualTo(true))
                .hasPathSatisfying("$.permits[3].match.siteRelation", v -> v.assertThat().isEqualTo("OTHER_STRUCTURE_ON_SITE"));
    }

    @Test
    void permitsFilterByStatusAndPage() {
        assertThat(mvc.get().uri("/api/v1/buildings/1/permits?status=active")).bodyJson()
                .hasPathSatisfying("$.total", v -> v.assertThat().isEqualTo(2))
                .hasPathSatisfying("$.permits[*].listing", v -> v.assertThat().asList().containsOnly("ACTIVE"));
        assertThat(mvc.get().uri("/api/v1/buildings/1/permits?status=cleared&limit=1&offset=1")).bodyJson()
                .hasPathSatisfying("$.total", v -> v.assertThat().isEqualTo(2))
                .hasPathSatisfying("$.permits[*].permitNumber", v -> v.assertThat().asList().containsExactly("99 100004 DEM"));
        assertThat(mvc.get().uri("/api/v1/buildings/1/permits?status=open")).hasStatus(HttpStatus.BAD_REQUEST);
        assertThat(mvc.get().uri("/api/v1/buildings/999/permits")).hasStatus(HttpStatus.NOT_FOUND);
    }

    @Test
    void permitsAtASharedAddressAreNotAttachedButAreFlagged() {
        assertThat(mvc.get().uri("/api/v1/buildings/4/permits")).bodyJson()
                .hasPathSatisfying("$.total", v -> v.assertThat().isEqualTo(0));
        assertThat(mvc.get().uri("/api/v1/buildings/4")).bodyJson()
                .hasPathSatisfying("$.coverageNotes", v -> v.assertThat().asList().contains("SOME_PERMITS_NOT_ATTACHED"));
    }

    @Test
    void evaluationsAreNewestFirst() {
        assertThat(mvc.get().uri("/api/v1/buildings/1/evaluations")).hasStatusOk().bodyJson()
                .hasPathSatisfying("$[*].evaluationDate", v -> v.assertThat().asList()
                        .containsExactly("2026-06-12", "2024-03-08", "2022-01-10"))
                .hasPathSatisfying("$[2].scoringVersion", v -> v.assertThat().isEqualTo("PRE_2023"));
    }

    @Test
    void unknownBuildingIs404ProblemDetail() {
        assertThat(mvc.get().uri("/api/v1/buildings/999")).hasStatus(HttpStatus.NOT_FOUND)
                .hasContentTypeCompatibleWith(MediaType.APPLICATION_PROBLEM_JSON);
        assertThat(mvc.get().uri("/api/v1/buildings/999/evaluations")).hasStatus(HttpStatus.NOT_FOUND);
    }

    @Test
    void websiteOriginIsAllowedByCors() {
        assertThat(mvc.options().uri("/api/v1/buildings/search?q=x")
                .header(HttpHeaders.ORIGIN, "http://localhost:3000")
                .header(HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD, "GET"))
                .hasStatusOk()
                .hasHeader(HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN, "http://localhost:3000");
        assertThat(mvc.options().uri("/api/v1/buildings/search?q=x")
                .header(HttpHeaders.ORIGIN, "https://evil.example")
                .header(HttpHeaders.ACCESS_CONTROL_REQUEST_METHOD, "GET"))
                .hasStatus(HttpStatus.FORBIDDEN);
    }

    @Test
    void openApiDescribesTheEndpoints() {
        assertThat(mvc.get().uri("/v3/api-docs")).hasStatusOk().bodyJson()
                .hasPathSatisfying("$.paths['/api/v1/buildings/search']", v -> v.assertThat().isNotNull())
                .hasPathSatisfying("$.paths['/api/v1/buildings/{id}']", v -> v.assertThat().isNotNull());
    }

    @Test
    void healthCheckIsUp() {
        assertThat(mvc.get().uri("/actuator/health")).hasStatusOk().bodyJson()
                .hasPathSatisfying("$.status", v -> v.assertThat().isEqualTo("UP"));
    }
}
