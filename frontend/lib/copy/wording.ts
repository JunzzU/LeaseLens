/**
 * Everything the product says to a renter, in one place. Framework-free so the mobile app can
 * reuse it. Rules (project plan, "Responsible presentation"): describe records, never judge a
 * building; say what is missing; "no record found" never means "no issue".
 */
import type { CoverageNote, EvaluationPoint, EvaluationSummary, MatchType, SearchResponse } from "../api/client";

export interface Note {
  title: string;
  body: string;
}

export const COVERAGE_NOTES: Record<CoverageNote, Note> = {
  BUILDING_NOT_UNIT: {
    title: "About the building, not a unit",
    body: "City evaluations cover the building and its common areas, such as lobbies, stairwells, laundry rooms and grounds. They say nothing about the condition of any particular apartment.",
  },
  NOT_IN_CURRENT_REGISTRATION: {
    title: "Not in the current registration list",
    body: "This building has past City records but isn't in the current RentSafeTO registration file. It may have been redeveloped or deregistered. Its past records are still shown.",
  },
  NO_EVALUATIONS: {
    title: "No evaluations yet",
    body: "The City hasn't published an evaluation for this building. That doesn't mean it has no issues.",
  },
  SCORING_SYSTEM_CHANGED: {
    title: "The City changed how it scores buildings",
    body: "In June 2023 the City switched to a new evaluation method with different items and scales. Scores from before and after can't be compared, so changes are only calculated within the same method.",
  },
  ADDRESS_SHARED_WITH_OTHER_BUILDING: {
    title: "Another building shares this address",
    body: "More than one registered building uses this address. Check the registration number (RSN) to make sure you're looking at the right one.",
  },
  SOME_PERMITS_NOT_ATTACHED: {
    title: "Some permits may be missing here",
    body: "Some permits were filed under an address this building shares with another. We couldn't tell which building they're for, so they aren't shown for either.",
  },
  NO_LOCATION: {
    title: "No map location",
    body: "The City hasn't published coordinates for this building.",
  },
};

export const NO_RECORD_IS_NOT_NO_ISSUE = "No record found doesn't mean no issue exists.";

export const LICENCE =
  "Contains information licensed under the Open Government Licence – Toronto. LeaseLens Toronto is an independent project and is not affiliated with or endorsed by the City of Toronto.";

export const SCORING_VERSION_LABEL = { V2023: "2023+ method", PRE_2023: "pre-2023 method" } as const;

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "2025-12-05" -> "Dec 5, 2025". Parsed by hand so the server's time zone can't shift the day. */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return `${MONTHS[m - 1]} ${d}, ${y}`;
}

const TORONTO = new Intl.DateTimeFormat("en-CA", {
  timeZone: "America/Toronto", year: "numeric", month: "2-digit", day: "2-digit",
});

/** The calendar date in Toronto of an instant, as "YYYY-MM-DD". */
function torontoDay(instant: Date): string {
  return TORONTO.format(instant); // en-CA formats as YYYY-MM-DD
}

/** A timestamp ("2026-09-22T03:19:00Z") as its Toronto calendar date: "Sep 21, 2026". */
export function formatTimestamp(iso: string): string {
  return formatDate(torontoDay(new Date(iso)));
}

/** Calendar days in Toronto between a timestamp and now: "today", "yesterday", "12 days ago". */
export function formatAge(iso: string, now: Date = new Date()): string {
  const day = (d: string) => Date.UTC(+d.slice(0, 4), +d.slice(5, 7) - 1, +d.slice(8, 10));
  const days = Math.round((day(torontoDay(now)) - day(torontoDay(new Date(iso)))) / 86_400_000);
  if (days <= 0) return "today";
  if (days === 1) return "yesterday";
  return `${days} days ago`;
}

/** Title-case City addresses for display: "181-183 GERRARD ST E" -> "181-183 Gerrard St E". */
export function formatAddress(address: string): string {
  return address
    .toLowerCase()
    .replace(/\b([a-z])/g, (c) => c.toUpperCase())
    .replace(/\b(Ne|Nw|Se|Sw)\b/g, (d) => d.toUpperCase());
}

/**
 * Addresses worth listing besides the main one. Numbers inside the building's own range
 * ("183" for "181-183 GERRARD ST E") are implied, so only genuinely different addresses remain.
 */
export function otherAddresses(address: string, known: string[]): string[] {
  const m = address.match(/^(\d+)[A-Z]?(?:-(\d+))?\s+(.+)$/);
  if (!m) return known.filter((a) => a !== address);
  const [low, high, street] = [Number(m[1]), Number(m[2] ?? m[1]), m[3]];
  return known.filter((a) => {
    const k = a.match(/^(\d+)[A-Z]?\s+(.+)$/);
    return !(k && k[2] === street && Number(k[1]) >= low && Number(k[1]) <= high);
  });
}

export function formatPropertyType(type: string | null): string | null {
  if (!type) return null;
  return { PRIVATE: "Private", TCHC: "Toronto Community Housing", "SOCIAL HOUSING": "Social housing" }[type] ?? type;
}

/** "Score 91 of 100 (2023+ method)". */
export function describeScore(p: EvaluationPoint): string {
  return `${p.score} of 100 (${SCORING_VERSION_LABEL[p.scoringVersion]})`;
}

/**
 * The change from the previous comparable evaluation, as plain fact:
 * "Up 19 points from Aug 4, 2023", "No change from ...", or null when there's nothing comparable.
 */
export function describeChange(e: EvaluationSummary): string | null {
  if (e.changeFromPrevious === null || !e.previous) return null;
  const since = `from ${formatDate(e.previous.date)}`;
  const n = e.changeFromPrevious;
  if (n === 0) return `No change ${since}`;
  const points = Math.abs(n) === 1 ? "point" : "points";
  return `${n > 0 ? "Up" : "Down"} ${Math.abs(n)} ${points} ${since}`;
}

/**
 * Said outright when the latest published evaluation is old, so an old score isn't read as current.
 * Three years is the longest interval the City's own evaluation results mention.
 */
export function evaluationAgeNote(latestDate: string, now: Date = new Date()): string | null {
  const [y, m, d] = latestDate.split("-").map(Number);
  const years = (now.getTime() - Date.UTC(y, m - 1, d)) / (365.25 * 86_400_000);
  if (years < 3) return null;
  return `This is the most recent evaluation the City has published for this building, from ${Math.floor(years)} years ago.`;
}

/** Why there's no change figure, when there isn't one. */
export function noChangeReason(e: EvaluationSummary): string | null {
  if (!e.latest) return null;
  if (e.changeFromPrevious !== null) return null;
  const sameMethod = e.countByScoringVersion[e.latest.scoringVersion] ?? 0;
  if (sameMethod <= 1 && e.count > 1) return "No earlier evaluation under the same method to compare with.";
  return "No earlier evaluation to compare with.";
}

/** The heading above search results; honest about how sure the match is. */
export function describeSearch(r: SearchResponse): string {
  const n = r.results.length;
  const count = `${n}${r.hasMore ? "+" : ""}`;
  const heading: Record<MatchType, string> = {
    ADDRESS: n > 1 ? `We found ${count} buildings at this address. Select the correct one.` : "We found this building.",
    PREFIX: `${count} ${n === 1 ? "address starts" : "addresses start"} with what you typed.`,
    STREET: `${count} RentSafeTO ${n === 1 ? "building" : "buildings"} on streets matching “${r.query}”.`,
    FUZZY: "No exact match. Did you mean one of these?",
    NONE: "No RentSafeTO building matches that address.",
  };
  return heading[r.matchType];
}

/** Shown when nothing matched: why that can happen. */
export const NO_MATCH_HELP =
  "RentSafeTO covers purpose-built rental apartment buildings with 3 or more storeys and 10 or more units. Condominiums, townhouses and rentals in houses aren't included. Check the street number and name, or try just the street name.";

/** Human names for the dataset codes the API uses in `sources`. */
export const DATASET_TITLES: Record<string, string> = {
  registration: "RentSafeTO building registration",
  evaluations_v2023: "RentSafeTO evaluations (2023 onward)",
  evaluations_pre2023: "RentSafeTO evaluations (before 2023, no longer updated)",
  permits_active: "Building permits: active",
  permits_cleared: "Building permits: closed since 2017",
};

export function datasetTitle(code: string): string {
  return DATASET_TITLES[code] ?? code;
}

export function plural(n: number, one: string, many = `${one}s`): string {
  return `${n.toLocaleString("en-CA")} ${n === 1 ? one : many}`;
}
