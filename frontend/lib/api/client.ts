/**
 * LeaseLens API client. Plain fetch and generated types only, no Next.js imports,
 * so the future mobile app can reuse this file unchanged.
 *
 * Types come from the backend's OpenAPI description: `npm run gen:api` (backend running).
 */
import type { components } from "./schema";

type Schemas = components["schemas"];

/**
 * The generator marks every field present (the API always sends every field), but it can't
 * tell which ones may be null. These are the fields the API documents as nullable.
 */
type WithNull<T, K extends keyof T> = Omit<T, K> & { [P in K]: T[P] | null };

export type SearchResult = WithNull<Schemas["SearchResult"], "wardName" | "storeys" | "units">;
export type SearchResponse = Omit<Schemas["SearchResponse"], "results"> & { results: SearchResult[] };
export type MatchType = SearchResponse["matchType"];
export type EvaluationPoint = Schemas["EvaluationPoint"];
export type EvaluationSummary = WithNull<Schemas["EvaluationSummary"], "latest" | "previous" | "changeFromPrevious">;
export type PermitSummary = WithNull<Schemas["PermitSummary"], "latestActivity">;
export type SourceFreshness = Schemas["SourceFreshness"];
export type BuildingSummary = WithNull<
  Omit<Schemas["BuildingSummary"], "evaluations" | "permits">,
  "location" | "postalFsa" | "ward" | "wardName" | "storeys" | "units" | "yearBuilt" | "yearRegistered" | "propertyType"
> & { evaluations: EvaluationSummary; permits: PermitSummary };
export type CoverageNote = Schemas["BuildingSummary"]["coverageNotes"][number];
export type EvaluationRecord = WithNull<Schemas["EvaluationRecord"], "score" | "proactiveScore" | "resultText">;
export type PermitRecord = WithNull<
  Schemas["PermitRecord"],
  "status" | "structureType" | "work" | "description" | "applicationDate" | "issuedDate" | "completedDate" | "estimatedCost"
>;
export type PermitPage = Omit<Schemas["PermitPage"], "permits"> & { permits: PermitRecord[] };
export type TimelineEvent = WithNull<Schemas["TimelineEvent"], "evaluation" | "permit">;
export type TimelinePage = Omit<Schemas["TimelinePage"], "events"> & { events: TimelineEvent[] };
export type Comparison = Schemas["Comparison"];
export type DataSourceStatus = Schemas["DataSourceStatus"];
export type Dataset = WithNull<Schemas["Dataset"], "lastSuccessfulImport" | "daysSinceSuccessfulImport">;

/** RFC 9457 problem detail, as every API error is returned. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(`API ${status}: ${detail}`);
  }
}

export interface ClientOptions {
  baseUrl: string;
  /** Passed through to every fetch, e.g. Next.js caching options. */
  init?: RequestInit;
}

type Params = Record<string, string | number | undefined>;

export function createClient({ baseUrl, init }: ClientOptions) {
  async function get<T>(path: string, params?: Params, signal?: AbortSignal): Promise<T> {
    const url = new URL(path, baseUrl);
    for (const [k, v] of Object.entries(params ?? {})) {
      if (v !== undefined) url.searchParams.set(k, String(v));
    }
    const res = await fetch(url, {
      ...init,
      signal: signal ?? init?.signal,
      headers: { Accept: "application/json", ...init?.headers },
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        detail = (await res.json()).detail ?? detail;
      } catch {
        // not a problem-detail body
      }
      throw new ApiError(res.status, detail);
    }
    return res.json() as Promise<T>;
  }

  return {
    /** Pass a signal to cancel an outdated search-as-you-type request. */
    search: (q: string, limit?: number, signal?: AbortSignal) =>
      get<SearchResponse>("/api/v1/buildings/search", { q, limit }, signal),
    building: (id: number) => get<BuildingSummary>(`/api/v1/buildings/${id}`),
    evaluations: (id: number) => get<EvaluationRecord[]>(`/api/v1/buildings/${id}/evaluations`),
    permits: (id: number, status: "active" | "cleared" | "all" = "all", limit = 50, offset = 0) =>
      get<PermitPage>(`/api/v1/buildings/${id}/permits`, { status, limit, offset }),
    timeline: (id: number, limit = 50, offset = 0) =>
      get<TimelinePage>(`/api/v1/buildings/${id}/timeline`, { limit, offset }),
    comparison: (id: number) => get<Comparison>(`/api/v1/buildings/${id}/comparison`),
    dataSources: () => get<DataSourceStatus>("/api/v1/data-sources/status"),
  };
}

export type LeaseLensClient = ReturnType<typeof createClient>;
