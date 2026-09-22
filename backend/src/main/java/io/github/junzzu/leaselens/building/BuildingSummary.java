package io.github.junzzu.leaselens.building;

import io.github.junzzu.leaselens.building.EvaluationRecord.ScoringVersion;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

/**
 * Everything the profile page needs in one call. Descriptive only: no rating, no verdict.
 * Explanations are returned as {@link CoverageNote} codes so each client words them itself.
 */
public record BuildingSummary(
        long id,
        @Schema(description = "RentSafeTO registration number (RSN)") String rsn,
        String address,
        @Schema(description = "Every address form this building is known by, e.g. each number of a range")
        List<String> knownAddresses,
        String postalFsa,
        String ward,
        String wardName,
        @Schema(description = "Null when the City published no coordinates") Location location,
        Integer storeys,
        Integer units,
        Integer yearBuilt,
        Integer yearRegistered,
        @Schema(example = "PRIVATE", description = "PRIVATE, TCHC or SOCIAL HOUSING") String propertyType,
        boolean rentSafeRegistered,
        EvaluationSummary evaluations,
        PermitSummary permits,
        List<CoverageNote> coverageNotes,
        List<SourceFreshness> sources) {

    public record Location(double latitude, double longitude) {}

    public record EvaluationSummary(
            int count,
            Map<ScoringVersion, Integer> countByScoringVersion,
            @Schema(description = "Null when the building has no evaluations") EvaluationPoint latest,
            @Schema(description = "The evaluation before latest under the same scoring version; null if none")
            EvaluationPoint previous,
            @Schema(description = "latest.score - previous.score; null when there is no comparable previous")
            Integer changeFromPrevious) {}

    public record PermitSummary(
            @Schema(description = "Attached permits in the City's active-permits file") int active,
            @Schema(description = "Attached permits that are closed, cancelled or completed") int cleared,
            @Schema(description = "Active permits for new construction or demolition on the property")
            int activeNewConstructionOrDemolition,
            @Schema(description = "Most recent issued (else application) date among attached permits; null if none")
            LocalDate latestActivity) {}

    public record EvaluationPoint(LocalDate date, Integer score, ScoringVersion scoringVersion) {}

    public record SourceFreshness(
            @Schema(example = "evaluations_v2023") String dataset,
            @Schema(description = "When LeaseLens last imported this dataset") OffsetDateTime lastImportedAt,
            @Schema(description = "The City's last-modified stamp for the file; not a guarantee of currency")
            String sourceVersion) {}

    public enum CoverageNote {
        /** Always present: evaluations cover the building and common areas, not any particular unit. */
        BUILDING_NOT_UNIT,
        /** Evaluated in the past but not in the current registration file. */
        NOT_IN_CURRENT_REGISTRATION,
        NO_EVALUATIONS,
        /** Has scores under both systems; the change is only computed within one system. */
        SCORING_SYSTEM_CHANGED,
        /** Another registered building shares one of this building's addresses. */
        ADDRESS_SHARED_WITH_OTHER_BUILDING,
        /** Some permits at this address were not attached because it is shared with another building. */
        SOME_PERMITS_NOT_ATTACHED,
        NO_LOCATION
    }
}
