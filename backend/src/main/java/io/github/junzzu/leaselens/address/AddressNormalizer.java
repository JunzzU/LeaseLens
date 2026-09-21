package io.github.junzzu.leaselens.address;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Toronto street-address normalization: {@code "123 Bloor Street West"}, {@code "123 BLOOR ST W"}
 * and {@code "123 Bloor St. W."} all become {@code 123|BLOOR|ST|W}.
 *
 * <p>Java port of the pipeline's normalizer. Any rule change must be made in both and
 * covered in testdata/address-normalization-cases.json.
 */
public final class AddressNormalizer {

    public static final Map<String, String> STREET_TYPES = Map.ofEntries(
            Map.entry("AVENUE", "AVE"), Map.entry("AVE", "AVE"), Map.entry("AV", "AVE"),
            Map.entry("STREET", "ST"), Map.entry("ST", "ST"),
            Map.entry("ROAD", "RD"), Map.entry("RD", "RD"),
            Map.entry("DRIVE", "DR"), Map.entry("DR", "DR"),
            Map.entry("BOULEVARD", "BLVD"), Map.entry("BLVD", "BLVD"),
            Map.entry("COURT", "CRT"), Map.entry("CRT", "CRT"), Map.entry("CT", "CRT"),
            Map.entry("CRESCENT", "CRES"), Map.entry("CRES", "CRES"),
            Map.entry("PLACE", "PL"), Map.entry("PL", "PL"),
            Map.entry("PARKWAY", "PKWY"), Map.entry("PKWY", "PKWY"),
            Map.entry("HEIGHTS", "HTS"), Map.entry("HTS", "HTS"),
            Map.entry("GARDENS", "GDNS"), Map.entry("GDNS", "GDNS"),
            Map.entry("CIRCUIT", "CRCT"), Map.entry("CRCT", "CRCT"),
            Map.entry("CIRCLE", "CRCL"), Map.entry("CRCL", "CRCL"),
            Map.entry("TERRACE", "TER"), Map.entry("TER", "TER"),
            Map.entry("GROVE", "GRV"), Map.entry("GRV", "GRV"),
            Map.entry("GATE", "GT"), Map.entry("GT", "GT"),
            Map.entry("SQUARE", "SQ"), Map.entry("SQ", "SQ"),
            Map.entry("TRAIL", "TRL"), Map.entry("TRL", "TRL"),
            Map.entry("LANE", "LANE"), Map.entry("LN", "LANE"),
            Map.entry("WAY", "WAY"), Map.entry("MALL", "MALL"), Map.entry("WALK", "WALK"),
            Map.entry("LINE", "LINE"), Map.entry("HILL", "HILL"), Map.entry("RIDGE", "RIDGE"),
            Map.entry("VISTA", "VISTA"), Map.entry("PATH", "PATH"), Map.entry("LANEWAY", "LANEWAY"),
            Map.entry("PROMENADE", "PROMENADE"), Map.entry("ESPLANADE", "ESPLANADE"), Map.entry("QUAY", "QUAY"));

    public static final Map<String, String> DIRECTIONS = Map.of(
            "E", "E", "EAST", "E", "W", "W", "WEST", "W", "N", "N", "NORTH", "N", "S", "S", "SOUTH", "S");

    private record Noise(Pattern pattern, String flag) {}

    /** Annotations the City appends to addresses. Stripped before parsing; recorded as flags. */
    private static final List<Noise> NOISE = List.of(
            new Noise(Pattern.compile("\\*\\*\\s*CREATED IN ERROR\\s*\\*\\*"), "created_in_error"),
            new Noise(Pattern.compile("<<[^>]*>>"), "annotation"),
            new Noise(Pattern.compile("-+\\s*CLOSED\\b"), "closed"),
            new Noise(Pattern.compile("-\\s*WARD\\s+\\d+\\b"), "annotation"));

    private static final Pattern DESIGNATOR =
            Pattern.compile("(?:-\\s*)?\\b(?:UNIT|BLDG|BUILDING|SUITE|APT)\\s+([A-Z0-9]+)\\s*$");
    private static final Pattern NUMBER =
            Pattern.compile("^(\\d+)\\s?([A-Z])?(?:\\s*-\\s*(\\d+)\\s?([A-Z])?)?\\s+(.+)$");
    private static final Pattern SPACES = Pattern.compile("\\s+");

    private AddressNormalizer() {}

    /** Result of {@link #clean}: the tidied text plus any annotation flags found. */
    public record Cleaned(String text, Set<String> flags) {}

    /** Upper-case, strip City annotations and punctuation, collapse whitespace. */
    public static Cleaned clean(String raw) {
        String s = raw == null ? "" : raw.toUpperCase(Locale.ROOT);
        Set<String> flags = new TreeSet<>();
        for (Noise noise : NOISE) {
            Matcher m = noise.pattern().matcher(s);
            if (m.find()) {
                flags.add(noise.flag());
                s = m.replaceAll(" ");
            }
        }
        s = s.replace('.', ' ').replace(',', ' ');
        return new Cleaned(SPACES.matcher(s).replaceAll(" ").strip(), Set.copyOf(flags));
    }

    public static Address parse(String raw) {
        Cleaned cleaned = clean(raw);
        String s = cleaned.text();

        String designator = "";
        Matcher d = DESIGNATOR.matcher(s);
        if (d.find()) {
            designator = d.group(1);
            s = s.substring(0, d.start()).strip();
        }

        Matcher m = NUMBER.matcher(s);
        if (!m.matches()) {
            throw new AddressParseException("no civic number in '" + raw + "'");
        }
        int low = Integer.parseInt(m.group(1));
        int high = m.group(3) != null ? Integer.parseInt(m.group(3)) : low;
        if (high < low) {
            throw new AddressParseException("descending range in '" + raw + "'");
        }

        List<String> words = new ArrayList<>(Arrays.asList(m.group(5).split(" ")));
        String direction = "";
        if (words.size() > 1 && DIRECTIONS.containsKey(words.getLast())) {
            direction = DIRECTIONS.get(words.removeLast());
        }
        String type = "";
        // The type is the last word, and never the only word ("THE KINGSWAY", "ST" in "ST CLAIR").
        if (words.size() > 1 && STREET_TYPES.containsKey(words.getLast())) {
            type = STREET_TYPES.get(words.removeLast());
        }
        if (words.isEmpty()) {
            throw new AddressParseException("no street name in '" + raw + "'");
        }
        String suffix = m.group(2) == null ? "" : m.group(2);
        return new Address(low, high, suffix, String.join(" ", words), type, direction, designator, cleaned.flags());
    }
}
