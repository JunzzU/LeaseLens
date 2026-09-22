package io.github.junzzu.leaselens.building;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.LocalDate;
import java.util.Map;

/**
 * How a building's latest evaluation compares with similar buildings'. Transparent by design:
 * the rule, the group size and the spread are always returned; the percentile only when the
 * group is large enough (docs/data-audit.md, finding 7).
 */
public record Comparison(
        long buildingId,
        Availability availability,
        @Schema(description = "The peer-selection rule used, with its parameters; null when no evaluation "
                + "could be compared")
        Rule rule,
        int peerCount,
        int minimumPeers,
        @Schema(description = "The building's latest 2023+ evaluation; older-method scores are never compared")
        Score target,
        @Schema(description = "Score spread among peers; null below minimumPeers") Spread peerScores,
        @Schema(description = "Percent of peers with a lower score; null below minimumPeers", example = "62")
        Integer percentOfPeersBelow,
        @Schema(description = "Percent of peers with exactly the same score; null below minimumPeers")
        Integer percentOfPeersEqual,
        PermitActivity permitActivity,
        @Schema(description = "Buildings that fit the size/location rule but have no 2023+ evaluation within the "
                + "window, so were left out (the missing-data rate)")
        int excludedWithoutRecentEvaluation,
        @Schema(description = "Property types in the peer group (PRIVATE, TCHC, SOCIAL HOUSING)")
        Map<String, Integer> peerPropertyTypes) {

    public enum Availability {
        AVAILABLE,
        /** Fewer than minimumPeers under every rule: counts shown, percentile withheld. */
        TOO_FEW_PEERS,
        /** No 2023+ evaluation to compare. */
        NO_CURRENT_EVALUATION,
        /** Storeys or units unknown, so similar buildings can't be selected. */
        MISSING_BUILDING_SIZE
    }

    /**
     * Tried in order; the first with at least {@link #MINIMUM_PEERS} peers is used. Every rule also
     * requires the peer's latest 2023+ evaluation to be within {@code EVALUATION_WINDOW_DAYS} of the
     * building's own.
     */
    public enum PeerRule {
        SAME_WARD_SIMILAR_SIZE(true, null, 25, 3),
        SAME_WARD_BROADER_SIZE(true, null, 50, 5),
        WITHIN_3_KM_BROADER_SIZE(false, 3000, 50, 5);

        public final boolean sameWard;
        public final Integer radiusMetres;
        public final int unitsWithinPercent;
        public final int storeysWithin;

        PeerRule(boolean sameWard, Integer radiusMetres, int unitsWithinPercent, int storeysWithin) {
            this.sameWard = sameWard;
            this.radiusMetres = radiusMetres;
            this.unitsWithinPercent = unitsWithinPercent;
            this.storeysWithin = storeysWithin;
        }
    }

    /** A {@link PeerRule} spelled out, so clients can state exactly who the building was compared with. */
    @Schema(name = "ComparisonRule")
    public record Rule(
            PeerRule code,
            boolean sameWard,
            @Schema(description = "Peers within this distance; null when the rule uses the ward") Integer radiusMetres,
            @Schema(description = "Peers' unit count within ± this percent") int unitsWithinPercent,
            @Schema(description = "Peers' storey count within ± this many storeys") int storeysWithin,
            @Schema(description = "Peers' latest evaluation within this many days of the building's") int evaluationWindowDays) {

        static Rule of(PeerRule r) {
            return r == null ? null : new Rule(r, r.sameWard, r.radiusMetres, r.unitsWithinPercent, r.storeysWithin,
                    EVALUATION_WINDOW_DAYS);
        }
    }

    public static final int MINIMUM_PEERS = 15;
    public static final int EVALUATION_WINDOW_DAYS = 730;

    @Schema(name = "ComparisonScore")
    public record Score(int score, LocalDate date) {}

    @Schema(name = "ScoreSpread")
    public record Spread(double median, double lowerQuartile, double upperQuartile, int min, int max) {}

    @Schema(name = "ComparisonPermitActivity")
    public record PermitActivity(
            @Schema(description = "Attached permits applied for in the last 5 years") int building,
            @Schema(description = "Median of the same count across peers; null below minimumPeers") Double peerMedian,
            Double peerUpperQuartile) {}
}
