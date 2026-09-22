package io.github.junzzu.leaselens.building;

import io.github.junzzu.leaselens.building.BuildingRepository.BuildingRow;
import io.github.junzzu.leaselens.building.Comparison.Availability;
import io.github.junzzu.leaselens.building.Comparison.PeerRule;
import io.github.junzzu.leaselens.building.Comparison.PermitActivity;
import io.github.junzzu.leaselens.building.Comparison.Score;
import io.github.junzzu.leaselens.building.ComparisonRepository.PeerCounts;
import io.github.junzzu.leaselens.building.ComparisonRepository.PeerStats;
import io.github.junzzu.leaselens.common.NotFoundException;
import java.time.Clock;
import java.time.LocalDate;
import java.util.Map;
import java.util.Optional;
import org.springframework.stereotype.Service;

@Service
public class ComparisonService {

    /** Permit activity is compared over this many recent years. */
    static final int PERMIT_YEARS = 5;

    private final BuildingRepository buildings;
    private final ComparisonRepository repository;
    private final Clock clock;

    public ComparisonService(BuildingRepository buildings, ComparisonRepository repository, Clock clock) {
        this.buildings = buildings;
        this.repository = repository;
        this.clock = clock;
    }

    public Comparison compare(long id) {
        BuildingRow b = buildings.findBuilding(id).orElseThrow(() -> new NotFoundException("building", id));
        LocalDate since = LocalDate.now(clock).minusYears(PERMIT_YEARS);
        int ownPermits = repository.recentPermitCount(id, since);
        PermitActivity ownOnly = new PermitActivity(ownPermits, null, null);

        if (b.storeys() == null || b.units() == null) {
            return unavailable(id, Availability.MISSING_BUILDING_SIZE, null, ownOnly);
        }
        Optional<Score> target = repository.latestCurrentScore(id);
        if (target.isEmpty()) {
            return unavailable(id, Availability.NO_CURRENT_EVALUATION, null, ownOnly);
        }

        PeerRule rule = null;
        PeerCounts counts = null;
        for (PeerRule candidate : PeerRule.values()) {
            if (candidate.radiusMetres != null && b.location() == null) {
                continue;   // a distance rule needs the building's coordinates
            }
            rule = candidate;
            counts = repository.count(id, candidate, since);
            if (counts.usable() >= Comparison.MINIMUM_PEERS) {
                break;
            }
        }

        Map<String, Integer> types = repository.propertyTypes(id, rule, since);
        if (counts.usable() < Comparison.MINIMUM_PEERS) {
            return new Comparison(id, Availability.TOO_FEW_PEERS, Comparison.Rule.of(rule), counts.usable(),
                    Comparison.MINIMUM_PEERS, target.get(), null, null, null, ownOnly, counts.excluded(), types);
        }
        PeerStats stats = repository.stats(id, rule, since);
        return new Comparison(id, Availability.AVAILABLE, Comparison.Rule.of(rule), counts.usable(),
                Comparison.MINIMUM_PEERS, target.get(), stats.spread(), stats.percentBelow(), stats.percentEqual(),
                new PermitActivity(ownPermits, stats.permitMedian(), stats.permitUpperQuartile()),
                counts.excluded(), types);
    }

    private static Comparison unavailable(long id, Availability why, Score target, PermitActivity permits) {
        return new Comparison(id, why, null, 0, Comparison.MINIMUM_PEERS, target, null, null, null, permits, 0,
                Map.of());
    }
}
