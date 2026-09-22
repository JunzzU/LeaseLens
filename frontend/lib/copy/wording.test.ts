import { describe, expect, it } from "vitest";
import type { EvaluationSummary, SearchResponse } from "../api/client";
import {
  COVERAGE_NOTES,
  describeChange,
  describeSearch,
  evaluationAgeNote,
  formatAddress,
  formatAge,
  formatDate,
  formatTimestamp,
  noChangeReason,
  otherAddresses,
} from "./wording";

const summary = (over: Partial<EvaluationSummary>): EvaluationSummary => ({
  count: 5,
  countByScoringVersion: { PRE_2023: 3, V2023: 2 },
  latest: { date: "2025-12-05", score: 91, scoringVersion: "V2023" },
  previous: { date: "2023-08-04", score: 72, scoringVersion: "V2023" },
  changeFromPrevious: 19,
  ...over,
});

describe("dates", () => {
  it("formats ISO dates without time-zone drift", () => {
    expect(formatDate("2025-12-05")).toBe("Dec 5, 2025");
    expect(formatDate("2026-01-01T00:30:00Z")).toBe("Jan 1, 2026");
    expect(formatDate(null)).toBe("—");
  });

  it("words import age in Toronto calendar days", () => {
    const now = new Date("2026-09-22T12:00:00Z"); // 8 am in Toronto
    expect(formatAge("2026-09-22T08:00:00Z", now)).toBe("today");
    expect(formatAge("2026-09-21T08:00:00Z", now)).toBe("yesterday");
    expect(formatAge("2026-09-10T12:00:00Z", now)).toBe("12 days ago");
    // 11:19 pm Sep 21 in Toronto is already Sep 22 in UTC: still "yesterday", not "today"
    expect(formatAge("2026-09-22T03:19:00Z", now)).toBe("yesterday");
  });

  it("shows timestamps as the Toronto date", () => {
    expect(formatTimestamp("2026-09-22T03:19:00Z")).toBe("Sep 21, 2026");
  });
});

describe("addresses", () => {
  it("lists only addresses not implied by the building's own range", () => {
    expect(otherAddresses("181-183 GERRARD ST E", ["181 GERRARD ST E", "183 GERRARD ST E"])).toEqual([]);
    expect(otherAddresses("385 CHURCH ST", ["385 CHURCH ST", "389 CHURCH ST"])).toEqual(["389 CHURCH ST"]);
    expect(otherAddresses("20 HOLLY ST", ["20 HOLLY ST", "40 SOUDAN AVE"])).toEqual(["40 SOUDAN AVE"]);
  });

  it("title-cases City addresses", () => {
    expect(formatAddress("181-183 GERRARD ST E")).toBe("181-183 Gerrard St E");
    expect(formatAddress("145 ST GEORGE ST")).toBe("145 St George St");
  });
});

describe("evaluation change", () => {
  it("states the change as fact, with the comparison date", () => {
    expect(describeChange(summary({}))).toBe("Up 19 points from Aug 4, 2023");
    expect(describeChange(summary({ changeFromPrevious: -1 }))).toBe("Down 1 point from Aug 4, 2023");
    expect(describeChange(summary({ changeFromPrevious: 0 }))).toBe("No change from Aug 4, 2023");
  });

  it("explains a missing change instead of comparing across methods", () => {
    const onlyOneNew = summary({ countByScoringVersion: { PRE_2023: 3, V2023: 1 }, previous: null, changeFromPrevious: null });
    expect(describeChange(onlyOneNew)).toBeNull();
    expect(noChangeReason(onlyOneNew)).toBe("No earlier evaluation under the same method to compare with.");
  });
});

describe("evaluation age", () => {
  const now = new Date("2026-09-22T12:00:00Z");
  it("says when the latest evaluation is years old", () => {
    expect(evaluationAgeNote("2019-11-26", now)).toBe(
      "This is the most recent evaluation the City has published for this building, from 6 years ago.");
  });
  it("stays quiet for recent evaluations", () => {
    expect(evaluationAgeNote("2025-12-05", now)).toBeNull();
  });
});

describe("search headings", () => {
  const response = (over: Partial<SearchResponse>): SearchResponse => ({
    query: "123 bloor", matchType: "ADDRESS", ambiguous: false, hasMore: false, results: [], ...over,
  });
  const result = { buildingId: 1, rsn: "1", address: "A", matchedAddress: "A", wardName: null, storeys: null, units: null, rentSafeRegistered: true };

  it("asks the user to choose when an address is ambiguous", () => {
    expect(describeSearch(response({ ambiguous: true, results: [result, result] })))
      .toBe("We found 2 buildings at this address. Select the correct one.");
  });

  it("is candid about fuzzy and empty results", () => {
    expect(describeSearch(response({ matchType: "FUZZY", results: [result] }))).toBe("No exact match. Did you mean one of these?");
    expect(describeSearch(response({ matchType: "NONE" }))).toBe("No RentSafeTO building matches that address.");
  });
});

describe("responsible wording", () => {
  const banned = /\b(safe|unsafe|good|bad|avoid|dangerous|problem-free|do not rent)\b/i;

  it("never uses verdict words in coverage notes", () => {
    for (const note of Object.values(COVERAGE_NOTES)) {
      expect(`${note.title} ${note.body}`).not.toMatch(banned);
    }
  });
});
