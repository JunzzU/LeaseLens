package io.github.junzzu.leaselens.building;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

/** Candidate buildings for an address query. Clients must let the user choose when {@code ambiguous}. */
public record SearchResponse(
        String query,
        @Schema(description = "How the results were found; the weakest method used decides how sure we are")
        MatchType matchType,
        @Schema(description = "More than one building matched: ask the user to pick, never pick for them")
        boolean ambiguous,
        @Schema(description = "More results exist than were returned; the user should refine the query")
        boolean hasMore,
        List<Result> results) {

    public enum MatchType {
        /** Civic number and street name matched; street type or direction may have been left out. */
        ADDRESS,
        /** The query is the start of an address ("123 BLO"). */
        PREFIX,
        /** No civic number given; every building on matching streets. */
        STREET,
        /** Nothing matched directly; these are similar-looking addresses ("did you mean"). */
        FUZZY,
        NONE
    }

    /** Carries enough detail to tell apart buildings that share an address. */
    @Schema(name = "SearchResult")
    public record Result(
            long buildingId,
            @Schema(description = "RentSafeTO registration number, shown when buildings share an address")
            String rsn,
            @Schema(example = "181-183 GERRARD ST E") String address,
            @Schema(description = "The address form that matched the query", example = "183 GERRARD ST E")
            String matchedAddress,
            String wardName,
            Integer storeys,
            Integer units,
            boolean rentSafeRegistered) {}
}
