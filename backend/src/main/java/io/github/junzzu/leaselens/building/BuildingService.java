package io.github.junzzu.leaselens.building;

import io.github.junzzu.leaselens.building.BuildingRepository.BuildingRow;
import io.github.junzzu.leaselens.building.BuildingSummary.CoverageNote;
import io.github.junzzu.leaselens.building.BuildingSummary.EvaluationPoint;
import io.github.junzzu.leaselens.building.BuildingSummary.EvaluationSummary;
import io.github.junzzu.leaselens.building.EvaluationRecord.ScoringVersion;
import io.github.junzzu.leaselens.common.NotFoundException;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;

@Service
public class BuildingService {

    private final BuildingRepository repository;
    private final PermitRepository permits;

    public BuildingService(BuildingRepository repository, PermitRepository permits) {
        this.repository = repository;
        this.permits = permits;
    }

    public BuildingSummary summary(long id) {
        BuildingRow b = repository.findBuilding(id).orElseThrow(() -> new NotFoundException("building", id));
        List<EvaluationRecord> evaluations = repository.findEvaluations(id);
        EvaluationSummary evalSummary = summarize(evaluations);

        List<CoverageNote> notes = new ArrayList<>();
        notes.add(CoverageNote.BUILDING_NOT_UNIT);
        if (!b.rentSafeRegistered()) {
            notes.add(CoverageNote.NOT_IN_CURRENT_REGISTRATION);
        }
        if (evaluations.isEmpty()) {
            notes.add(CoverageNote.NO_EVALUATIONS);
        }
        if (evalSummary.countByScoringVersion().size() > 1) {
            notes.add(CoverageNote.SCORING_SYSTEM_CHANGED);
        }
        if (repository.sharesAddressWithAnotherBuilding(id)) {
            notes.add(CoverageNote.ADDRESS_SHARED_WITH_OTHER_BUILDING);
        }
        if (permits.hasUnattachedSharedAddressPermits(id)) {
            notes.add(CoverageNote.SOME_PERMITS_NOT_ATTACHED);
        }
        if (b.location() == null) {
            notes.add(CoverageNote.NO_LOCATION);
        }

        return new BuildingSummary(b.id(), b.rsn(), b.address(), repository.findAliases(id), b.postalFsa(), b.ward(),
                b.wardName(), b.location(), b.storeys(), b.units(), b.yearBuilt(), b.yearRegistered(),
                b.propertyType(), b.rentSafeRegistered(), evalSummary, permits.summarize(id), List.copyOf(notes),
                repository.findSourceFreshness());
    }

    public PermitRecord.Page permits(long id, PermitRecord.Listing listing, int limit, int offset) {
        repository.findBuilding(id).orElseThrow(() -> new NotFoundException("building", id));
        BuildingSummary.PermitSummary counts = permits.summarize(id);
        int total = listing == null ? counts.active() + counts.cleared()
                : listing == PermitRecord.Listing.ACTIVE ? counts.active() : counts.cleared();
        return new PermitRecord.Page(total, counts.active(), counts.cleared(), limit, offset,
                permits.find(id, listing, limit, offset));
    }

    public void requireExists(long id) {
        repository.findBuilding(id).orElseThrow(() -> new NotFoundException("building", id));
    }

    public List<EvaluationRecord> evaluations(long id) {
        repository.findBuilding(id).orElseThrow(() -> new NotFoundException("building", id));
        return repository.findEvaluations(id);
    }

    /**
     * Latest evaluation, and the change from the one before it under the same scoring
     * version. Scores from different versions are never subtracted: the 2023 method
     * change alone moved the median from 74 to 91.
     */
    static EvaluationSummary summarize(List<EvaluationRecord> newestFirst) {
        Map<ScoringVersion, Integer> counts = new EnumMap<>(ScoringVersion.class);
        newestFirst.forEach(e -> counts.merge(e.scoringVersion(), 1, Integer::sum));
        if (newestFirst.isEmpty()) {
            return new EvaluationSummary(0, counts, null, null, null);
        }
        EvaluationRecord latest = newestFirst.getFirst();
        EvaluationRecord previous = newestFirst.stream().skip(1)
                .filter(e -> e.scoringVersion() == latest.scoringVersion())
                .findFirst().orElse(null);
        Integer change = previous != null && latest.score() != null && previous.score() != null
                ? latest.score() - previous.score() : null;
        return new EvaluationSummary(newestFirst.size(), counts, point(latest), point(previous), change);
    }

    private static EvaluationPoint point(EvaluationRecord e) {
        return e == null ? null : new EvaluationPoint(e.evaluationDate(), e.score(), e.scoringVersion());
    }
}
