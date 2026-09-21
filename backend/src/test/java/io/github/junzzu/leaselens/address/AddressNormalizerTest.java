package io.github.junzzu.leaselens.address;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.nio.file.Path;
import java.util.List;
import java.util.stream.Stream;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.MethodSource;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

/** Runs the cases shared with the Python pipeline, so both normalizers stay identical. */
class AddressNormalizerTest {

    private static final JsonNode CASES = JsonMapper.builder().build()
            .readTree(Path.of("../testdata/address-normalization-cases.json").toFile());

    static Stream<JsonNode> sharedCases() {
        return CASES.get("cases").valueStream();
    }

    static Stream<String> invalidInputs() {
        return CASES.get("invalid").valueStream().map(JsonNode::asString);
    }

    @ParameterizedTest(name = "{0}")
    @MethodSource("sharedCases")
    void matchesSharedCase(JsonNode c) {
        Address a = AddressNormalizer.parse(c.get("input").asString());

        assertThat(a.key()).isEqualTo(c.get("key").asString());
        assertThat(a.expandKeys()).isEqualTo(strings(c.get("keys")));
        assertThat(a.designator()).isEqualTo(c.has("designator") ? c.get("designator").asString() : "");
        assertThat(a.flags()).containsExactlyInAnyOrderElementsOf(c.has("flags") ? strings(c.get("flags")) : List.of());
    }

    @ParameterizedTest
    @MethodSource("invalidInputs")
    void rejectsInvalid(String raw) {
        assertThatThrownBy(() -> AddressNormalizer.parse(raw)).isInstanceOf(AddressParseException.class);
    }

    private static List<String> strings(JsonNode array) {
        return array.valueStream().map(JsonNode::asString).toList();
    }
}
