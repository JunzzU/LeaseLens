package io.github.junzzu.leaselens.address;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * A parsed Toronto street address. Mirrors {@code Address} in the Python pipeline
 * (pipeline/src/leaselens_pipeline/normalization/address.py); both must agree on
 * testdata/address-normalization-cases.json.
 */
public record Address(
        int numberLow,
        int numberHigh,
        String suffix,
        String streetName,
        String streetType,
        String direction,
        String designator,
        Set<String> flags) {

    /** Ranges wider than this are expanded to their endpoints only. */
    static final int MAX_RANGE_SPAN = 40;

    /** Key of the first civic number, e.g. {@code 85|THORNCLIFFE PARK|DR|}. */
    public String key() {
        return makeKey(numberLow, suffix, streetName, streetType, direction);
    }

    public boolean isRange() {
        return numberHigh != numberLow;
    }

    /** One key per civic number the range covers, stepping by 2 (same side of the street). */
    public List<String> expandKeys() {
        if (!isRange()) {
            return List.of(key());
        }
        int span = numberHigh - numberLow;
        List<Integer> numbers = new ArrayList<>();
        if (span > MAX_RANGE_SPAN) {
            numbers.add(numberLow);
            numbers.add(numberHigh);
        } else {
            int step = span % 2 == 0 ? 2 : 1;
            for (int n = numberLow; n <= numberHigh; n += step) {
                numbers.add(n);
            }
        }
        return numbers.stream()
                .map(n -> makeKey(n, n == numberLow ? suffix : "", streetName, streetType, direction))
                .toList();
    }

    static String makeKey(int number, String suffix, String name, String type, String direction) {
        return number + suffix + "|" + name + "|" + type + "|" + direction;
    }
}
