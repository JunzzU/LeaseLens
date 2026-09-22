package io.github.junzzu.leaselens.datasource;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.OffsetDateTime;
import java.util.List;

/** Where every record comes from and how fresh it is, for the "About the data" page. */
public record DataSourceStatus(
        List<Dataset> datasets,
        @Schema(description = "Attribution that must accompany the data") String licence) {

    public static final String LICENCE = "Contains information licensed under the Open Government Licence – "
            + "Toronto. LeaseLens Toronto is an independent project and is not affiliated with or endorsed by the "
            + "City of Toronto.";

    public record Dataset(
            @Schema(example = "evaluations_v2023") String dataset,
            @Schema(example = "Apartment Building Evaluations (2023 – current)") String title,
            @Schema(description = "The City's page for the dataset") String portalUrl,
            @Schema(description = "False for archives the City no longer updates") boolean updatedByCity,
            @Schema(description = "Null if the dataset has never been imported successfully")
            Import lastSuccessfulImport,
            @Schema(description = "The most recent attempt, successful or not") Attempt lastAttempt,
            @Schema(description = "Whole days since the last successful import; null if never")
            Integer daysSinceSuccessfulImport) {}

    @Schema(name = "DatasetImport")
    public record Import(
            OffsetDateTime importedAt,
            @Schema(description = "The City's last-modified stamp for the file. It says when the portal file "
                    + "changed, not that every record in it is current.") String sourceVersion,
            Integer recordCount) {}

    @Schema(name = "ImportAttempt")
    public record Attempt(OffsetDateTime startedAt, String status) {}
}
