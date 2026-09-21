package io.github.junzzu.leaselens.building;

import static io.github.junzzu.leaselens.building.EvaluationRecord.ScoringVersion.PRE_2023;
import static io.github.junzzu.leaselens.building.EvaluationRecord.ScoringVersion.V2023;
import static org.assertj.core.api.Assertions.assertThat;

import io.github.junzzu.leaselens.building.BuildingSummary.EvaluationSummary;
import io.github.junzzu.leaselens.building.EvaluationRecord.ScoringVersion;
import java.time.LocalDate;
import java.util.List;
import org.junit.jupiter.api.Test;

class BuildingServiceTest {

    private static EvaluationRecord eval(String date, int score, ScoringVersion v) {
        return new EvaluationRecord(LocalDate.parse(date), v, score, null, null, null, null);
    }

    @Test
    void changeIsNeverComputedAcrossScoringVersions() {
        // One V2023 evaluation after two PRE_2023 ones: there is no comparable previous score.
        EvaluationSummary s = BuildingService.summarize(List.of(
                eval("2024-01-01", 91, V2023), eval("2022-01-01", 74, PRE_2023), eval("2020-01-01", 70, PRE_2023)));

        assertThat(s.latest().score()).isEqualTo(91);
        assertThat(s.previous()).isNull();
        assertThat(s.changeFromPrevious()).isNull();
        assertThat(s.countByScoringVersion()).containsEntry(V2023, 1).containsEntry(PRE_2023, 2);
    }

    @Test
    void changeUsesThePreviousEvaluationOfTheSameVersion() {
        EvaluationSummary s = BuildingService.summarize(List.of(
                eval("2026-01-01", 78, V2023), eval("2024-01-01", 84, V2023), eval("2022-01-01", 60, PRE_2023)));

        assertThat(s.previous().date()).isEqualTo(LocalDate.parse("2024-01-01"));
        assertThat(s.changeFromPrevious()).isEqualTo(-6);
    }

    @Test
    void noEvaluations() {
        EvaluationSummary s = BuildingService.summarize(List.of());
        assertThat(s.count()).isZero();
        assertThat(s.latest()).isNull();
    }

    @Test
    void searchPatternLeavesOmittedPartsOpen() {
        assertThat(BuildingSearchService.exactPattern("123", "BLOOR")).isEqualTo("123|BLOOR|%|%");
        assertThat(BuildingSearchService.exactPattern("123", "BLOOR W")).isEqualTo("123|BLOOR|%|W");
        assertThat(BuildingSearchService.exactPattern("123", "BLOOR STREET WEST")).isEqualTo("123|BLOOR|ST|W");
        assertThat(BuildingSearchService.exactPattern("145", "ST GEORGE ST")).isEqualTo("145|ST GEORGE|ST|%");
        assertThat(BuildingSearchService.normalizeStreet("GERRARD STREET EAST")).isEqualTo("GERRARD ST E");
    }
}
