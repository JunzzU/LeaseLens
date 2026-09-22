package io.github.junzzu.leaselens.building;

import io.github.junzzu.leaselens.building.EvaluationRecord.ScoringVersion;
import io.github.junzzu.leaselens.building.PermitRecord.Listing;
import io.github.junzzu.leaselens.building.PermitRecord.WorkCategory;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDate;
import java.util.List;

/**
 * One dated event in a building's history. Structured, not prose: each client words it.
 * Exactly one of {@code evaluation} / {@code permit} is set for evaluation and permit events.
 */
public record TimelineEvent(
        LocalDate date,
        @Schema(description = "DAY or MONTH: how exact `date` is (the scoring-system change is dated by month)")
        DatePrecision datePrecision,
        Type type,
        @Schema(description = "Dataset the event comes from", example = "permits_active")
        String source,
        Evaluation evaluation,
        Permit permit) {

    public enum Type {
        EVALUATION,
        PERMIT_APPLIED,
        PERMIT_ISSUED,
        /** Completed, closed or cancelled; see permit.status. */
        PERMIT_CLOSED,
        /** June 2023: the City changed the evaluation method; scores before and after are not comparable. */
        SCORING_SYSTEM_CHANGE
    }

    public enum DatePrecision { DAY, MONTH }

    public record Evaluation(Integer score, ScoringVersion scoringVersion) {}

    public record Permit(
            String permitNumber,
            String permitType,
            String status,
            Listing listing,
            WorkCategory workCategory,
            String siteRelation,
            String description,
            boolean predatesBuilding) {}

    public record Page(int total, int limit, int offset, List<TimelineEvent> events) {}
}
