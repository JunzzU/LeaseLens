package io.github.junzzu.leaselens.building;

import io.swagger.v3.oas.annotations.media.Schema;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.List;

/** A City of Toronto building permit attached to a building, with the evidence for the match. */
public record PermitRecord(
        String permitNumber,
        String revisionNumber,
        String permitType,
        @Schema(description = "ACTIVE: in the City's active-permits file; CLEARED: closed, cancelled or completed")
        Listing listing,
        @Schema(example = "Inspection") String status,
        @Schema(description = "Work on the existing building, or new construction / demolition on the site")
        WorkCategory workCategory,
        String work,
        String structureType,
        String description,
        LocalDate applicationDate,
        LocalDate issuedDate,
        LocalDate completedDate,
        @Schema(description = "The applicant's estimate; null when the City's field holds no number")
        BigDecimal estimatedCost,
        Integer dwellingUnitsCreated,
        Integer dwellingUnitsLost,
        @Schema(description = "Applied for before the building's year built: likely about an earlier structure "
                + "or this building's own construction")
        boolean predatesBuilding,
        Match match,
        OffsetDateTime importedAt) {

    public enum Listing { ACTIVE, CLEARED }

    public enum WorkCategory { ALTERATION_OR_REPAIR, NEW_CONSTRUCTION, DEMOLITION }

    @Schema(name = "PermitMatch")
    public record Match(
            @Schema(description = "ADDRESS: same civic address; PERMIT_RANGE: the permit's address range covers it")
            String method,
            @Schema(description = "HIGH or MEDIUM; only unambiguous matches are returned")
            String confidence,
            @Schema(description = "BUILDING, NON_RESIDENTIAL_SPACE (a shop or office in or on the building), "
                    + "or OTHER_STRUCTURE_ON_SITE (e.g. townhouses on the same property)")
            String siteRelation,
            @Schema(description = "The permit's address as the City published it", example = "2721-2729 VICTORIA PARK AVE")
            String permitAddress) {}

    /** One page of a building's permits plus totals, so clients can show counts without fetching all. */
    @Schema(name = "PermitPage")
    public record Page(
            int total,
            int activeCount,
            int clearedCount,
            int limit,
            int offset,
            List<PermitRecord> permits) {}
}
