package io.github.junzzu.leaselens.building;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;
import java.util.List;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/buildings")
@Validated
@Tag(name = "Buildings")
public class BuildingController {

    private final BuildingSearchService search;
    private final BuildingService buildings;

    public BuildingController(BuildingSearchService search, BuildingService buildings) {
        this.search = search;
        this.buildings = buildings;
    }

    @GetMapping("/search")
    @Operation(summary = "Find buildings by address",
            description = "Returns candidates, never a single silent guess. When `ambiguous` is true the client "
                    + "must ask the user to choose. `matchType` says how certain the match is.")
    public SearchResponse search(
            @Parameter(example = "181 gerrard st e") @RequestParam @NotBlank @Size(max = 100) String q,
            @RequestParam(required = false) @Min(1) @Max(50) Integer limit) {
        return search.search(q, limit);
    }

    @GetMapping("/{id}")
    @Operation(summary = "Building profile: details, evaluation summary, coverage notes and data freshness")
    public BuildingSummary summary(@PathVariable long id) {
        return buildings.summary(id);
    }

    @GetMapping("/{id}/permits")
    @Operation(summary = "Building permits attached to a building, newest activity first",
            description = "Only permits whose address matches this building and no other are returned. Each "
                    + "carries its match evidence. Permits can indicate maintenance, renovation or construction; "
                    + "they are not a judgement of the building.")
    public PermitRecord.Page permits(
            @PathVariable long id,
            @Parameter(description = "active, cleared or all") @RequestParam(defaultValue = "all")
            @Pattern(regexp = "active|cleared|all") String status,
            @RequestParam(defaultValue = "50") @Min(1) @Max(200) int limit,
            @RequestParam(defaultValue = "0") @Min(0) int offset) {
        PermitRecord.Listing listing = switch (status) {
            case "active" -> PermitRecord.Listing.ACTIVE;
            case "cleared" -> PermitRecord.Listing.CLEARED;
            default -> null;
        };
        return buildings.permits(id, listing, limit, offset);
    }

    @GetMapping("/{id}/evaluations")
    @Operation(summary = "All RentSafeTO evaluations for a building, newest first")
    public List<EvaluationRecord> evaluations(@PathVariable long id) {
        return buildings.evaluations(id);
    }
}
