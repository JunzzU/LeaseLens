package io.github.junzzu.leaselens.building;

import io.github.junzzu.leaselens.address.AddressNormalizer;
import io.github.junzzu.leaselens.building.SearchResponse.MatchType;
import io.github.junzzu.leaselens.building.SearchResponse.Result;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/**
 * Address search. Tries the most certain method first and stops at the first that finds
 * anything: exact number + street, then prefix (search-as-you-type), then street-only or
 * fuzzy. The method used is returned so the UI can word its answer honestly.
 */
@Service
public class BuildingSearchService {

    private static final Pattern NUMBERED = Pattern.compile("^(\\d+)\\s?([A-Z])?(?:\\s*-\\s*\\d+)?(?:\\s+(.*))?$");
    private static final Pattern UNSAFE = Pattern.compile("[^A-Z0-9 -]");

    private final BuildingRepository repository;
    private final int maxResults;

    public BuildingSearchService(BuildingRepository repository,
                                 @Value("${leaselens.search.max-results}") int maxResults) {
        this.repository = repository;
        this.maxResults = maxResults;
    }

    public SearchResponse search(String query, Integer limit) {
        int n = limit == null ? maxResults : Math.clamp(limit, 1, maxResults);
        String q = UNSAFE.matcher(AddressNormalizer.clean(query).text()).replaceAll("").strip();

        Matcher m = NUMBERED.matcher(q);
        if (m.matches()) {
            String number = m.group(1) + (m.group(2) == null ? "" : m.group(2));
            String rest = m.group(3) == null ? "" : m.group(3).strip();
            if (rest.isEmpty()) {
                return respond(query, MatchType.PREFIX, repository.searchByKeyPattern(number + "|%", n + 1), n);
            }
            List<Result> exact = repository.searchByKeyPattern(exactPattern(number, rest), n + 1);
            if (!exact.isEmpty()) {
                return respond(query, MatchType.ADDRESS, exact, n);
            }
            List<Result> prefix = repository.searchByKeyPattern(number + "|" + like(rest) + "%", n + 1);
            if (!prefix.isEmpty()) {
                return respond(query, MatchType.PREFIX, prefix, n);
            }
        } else if (!q.isEmpty()) {
            List<Result> street = repository.searchByStreet(like(normalizeStreet(q)), n + 1);
            if (!street.isEmpty()) {
                return respond(query, MatchType.STREET, street, n);
            }
        }
        List<Result> fuzzy = q.isEmpty() ? List.of() : repository.searchFuzzy(q, n + 1);
        return respond(query, fuzzy.isEmpty() ? MatchType.NONE : MatchType.FUZZY, fuzzy, n);
    }

    /**
     * Key pattern for "number street [type] [direction]". A type or direction the user left
     * out matches any, so "123 bloor" finds both 123 BLOOR ST E and 123 BLOOR ST W.
     */
    static String exactPattern(String number, String rest) {
        List<String> words = new ArrayList<>(Arrays.asList(rest.split(" ")));
        String direction = "%";
        if (words.size() > 1 && AddressNormalizer.DIRECTIONS.containsKey(words.getLast())) {
            direction = AddressNormalizer.DIRECTIONS.get(words.removeLast());
        }
        String type = "%";
        if (words.size() > 1 && AddressNormalizer.STREET_TYPES.containsKey(words.getLast())) {
            type = AddressNormalizer.STREET_TYPES.get(words.removeLast());
        }
        return number + "|" + like(String.join(" ", words)) + "|" + type + "|" + direction;
    }

    /** "GERRARD STREET EAST" -> "GERRARD ST E", so it matches the stored abbreviations. */
    static String normalizeStreet(String street) {
        List<String> words = new ArrayList<>(Arrays.asList(street.split(" ")));
        String direction = "";
        if (words.size() > 1 && AddressNormalizer.DIRECTIONS.containsKey(words.getLast())) {
            direction = AddressNormalizer.DIRECTIONS.get(words.removeLast());
        }
        if (words.size() > 1 && AddressNormalizer.STREET_TYPES.containsKey(words.getLast())) {
            words.add(AddressNormalizer.STREET_TYPES.get(words.removeLast()));
        }
        if (!direction.isEmpty()) {
            words.add(direction);
        }
        return String.join(" ", words);
    }

    /** Escape LIKE wildcards. The input is already reduced to [A-Z0-9 -], so this is belt and braces. */
    private static String like(String s) {
        return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_");
    }

    private static SearchResponse respond(String query, MatchType type, List<Result> rows, int limit) {
        boolean hasMore = rows.size() > limit;
        List<Result> results = hasMore ? rows.subList(0, limit) : rows;
        return new SearchResponse(query, type, results.size() > 1, hasMore, List.copyOf(results));
    }
}
