package io.github.junzzu.leaselens.building;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDate;
import java.time.OffsetDateTime;

/** One RentSafeTO evaluation as published by the City. */
public record EvaluationRecord(
        LocalDate evaluationDate,
        ScoringVersion scoringVersion,
        @Schema(description = "Overall score, 0-100. Only comparable with scores of the same scoringVersion")
        Integer score,
        @Schema(description = "V2023 only: score from the proactive (scheduled) evaluation")
        Integer proactiveScore,
        Integer areasEvaluated,
        @Schema(description = "PRE_2023 only: the City's note on when the next evaluation is due")
        String resultText,
        @Schema(description = "When LeaseLens last imported this record")
        OffsetDateTime importedAt) {

    public enum ScoringVersion {
        /** 2017-09 to 2023-05: ~20 items scored 1-5. Median score 74. */
        PRE_2023,
        /** 2023-06 onward: ~50 items scored 0-3. Median score 91. */
        V2023
    }
}
