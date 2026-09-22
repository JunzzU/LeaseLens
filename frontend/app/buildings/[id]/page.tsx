import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { cache } from "react";
import { ApiError, type BuildingSummary } from "@/lib/api/client";
import { api } from "@/lib/api/server";
import {
  COVERAGE_NOTES,
  datasetTitle,
  describeChange,
  evaluationAgeNote,
  formatAddress,
  formatAge,
  formatDate,
  formatTimestamp,
  formatPropertyType,
  NO_RECORD_IS_NOT_NO_ISSUE,
  noChangeReason,
  otherAddresses,
  plural,
  SCORING_VERSION_LABEL,
} from "@/lib/copy/wording";

/** One fetch per request, shared by generateMetadata and the page. */
const loadBuilding = cache(async (rawId: string): Promise<BuildingSummary> => {
  const id = Number(rawId);
  if (!Number.isSafeInteger(id) || id <= 0) notFound();
  try {
    return await api.building(id);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }
});

export async function generateMetadata({ params }: PageProps<"/buildings/[id]">): Promise<Metadata> {
  const b = await loadBuilding((await params).id);
  return {
    title: formatAddress(b.address),
    description: `City evaluations and building permits for ${formatAddress(b.address)}, Toronto, with sources and dates.`,
  };
}

export default async function BuildingPage({ params }: PageProps<"/buildings/[id]">) {
  const b = await loadBuilding((await params).id);
  return (
    <article className="space-y-8">
      <BuildingHeader b={b} others={otherAddresses(b.address, b.knownAddresses)} />
      <CoverageNotes b={b} />
      <div className="grid gap-6 md:grid-cols-2">
        <EvaluationsCard b={b} />
        <PermitsCard b={b} />
      </div>
      <Sources b={b} />
    </article>
  );
}

function BuildingHeader({ b, others }: { b: BuildingSummary; others: string[] }) {
  const facts = [
    ["Ward", b.wardName ?? (b.ward ? `Ward ${b.ward}` : null)],
    ["Storeys", b.storeys],
    ["Units", b.units],
    ["Built", b.yearBuilt],
    ["Ownership", formatPropertyType(b.propertyType)],
    ["Registration number", b.rsn],
  ].filter(([, v]) => v !== null && v !== undefined);

  return (
    <header className="space-y-4">
      <div className="space-y-1">
        <h1 className="font-serif text-3xl font-semibold tracking-tight sm:text-4xl">{formatAddress(b.address)}</h1>
        {others.length > 0 && <p className="text-muted">Also listed as {others.map(formatAddress).join(", ")}</p>}
        <p className="text-sm text-muted">
          {b.rentSafeRegistered ? "Registered with RentSafeTO" : "Not in the current RentSafeTO registration list"}
        </p>
      </div>
      <dl className="grid grid-cols-2 gap-x-6 gap-y-3 rounded-lg border border-line bg-card p-4 sm:grid-cols-3 lg:grid-cols-6">
        {facts.map(([label, value]) => (
          <div key={label as string}>
            <dt className="text-xs uppercase tracking-wide text-muted">{label}</dt>
            <dd className="font-medium">{value}</dd>
          </div>
        ))}
      </dl>
    </header>
  );
}

/** Caveats specific to this building. BUILDING_NOT_UNIT applies to every building, so it sits with the scores. */
function CoverageNotes({ b }: { b: BuildingSummary }) {
  const notes = b.coverageNotes.filter((c) => c !== "BUILDING_NOT_UNIT");
  if (notes.length === 0) return null;
  return (
    <section aria-labelledby="notes-heading" className="rounded-lg border border-note-line bg-note px-5 py-4 text-note-ink">
      <h2 id="notes-heading" className="font-medium">
        What to know about these records
      </h2>
      <ul className="mt-2 space-y-2 text-sm">
        {notes.map((code) => (
          <li key={code}>
            <span className="font-medium">{COVERAGE_NOTES[code].title}.</span> {COVERAGE_NOTES[code].body}
          </li>
        ))}
      </ul>
    </section>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  const id = title.toLowerCase().replace(/\W+/g, "-");
  return (
    <section aria-labelledby={id} className="space-y-4 rounded-lg border border-line bg-card p-5">
      <h2 id={id} className="font-serif text-xl font-semibold">
        {title}
      </h2>
      {children}
    </section>
  );
}

function EvaluationsCard({ b }: { b: BuildingSummary }) {
  const e = b.evaluations;
  if (!e.latest) {
    return (
      <Card title="City evaluations">
        <p>No RentSafeTO evaluation has been published for this building.</p>
        <p className="text-sm text-muted">{NO_RECORD_IS_NOT_NO_ISSUE}</p>
      </Card>
    );
  }
  const change = describeChange(e);
  const ageNote = evaluationAgeNote(e.latest.date);
  const byVersion = (["V2023", "PRE_2023"] as const)
    .filter((v) => e.countByScoringVersion[v])
    .map((v) => `${e.countByScoringVersion[v]} under the ${SCORING_VERSION_LABEL[v]}`);

  return (
    <Card title="City evaluations">
      <div>
        <p className="text-sm text-muted">Latest available score</p>
        <p className="font-serif text-5xl font-semibold">
          {e.latest.score}
          <span className="text-2xl text-muted"> / 100</span>
        </p>
        <p className="text-sm text-muted">
          Evaluated {formatDate(e.latest.date)} · {SCORING_VERSION_LABEL[e.latest.scoringVersion]}
        </p>
      </div>
      {ageNote && <p className="rounded-md bg-note px-3 py-2 text-sm text-note-ink">{ageNote}</p>}
      <p>{change ?? noChangeReason(e)}</p>
      <p className="text-sm text-muted">
        {plural(e.count, "evaluation")} on record{byVersion.length ? `: ${byVersion.join(", ")}` : ""}.
      </p>
      <p className="text-sm text-muted">{COVERAGE_NOTES.BUILDING_NOT_UNIT.body}</p>
    </Card>
  );
}

function PermitsCard({ b }: { b: BuildingSummary }) {
  const p = b.permits;
  const total = p.active + p.cleared;
  return (
    <Card title="Building permits">
      {total === 0 ? (
        <>
          <p>No permits found under this building&apos;s address in the City&apos;s records.</p>
          <p className="text-sm text-muted">{NO_RECORD_IS_NOT_NO_ISSUE}</p>
        </>
      ) : (
        <>
          <dl className="grid grid-cols-2 gap-4">
            <div>
              <dt className="text-sm text-muted">Active</dt>
              <dd className="font-serif text-4xl font-semibold">{p.active}</dd>
            </div>
            <div>
              <dt className="text-sm text-muted">Closed since 2017</dt>
              <dd className="font-serif text-4xl font-semibold">{p.cleared}</dd>
            </div>
          </dl>
          {p.activeNewConstructionOrDemolition > 0 && (
            <p>
              {plural(p.activeNewConstructionOrDemolition, "active permit")} for new construction or demolition on
              this property.
            </p>
          )}
          {p.latestActivity && <p className="text-sm text-muted">Most recent permit activity: {formatDate(p.latestActivity)}</p>}
        </>
      )}
      <p className="text-sm text-muted">
        Permits can mean maintenance, renovation, new construction or a safety upgrade. They aren&apos;t a judgement of
        the building.
      </p>
    </Card>
  );
}

function Sources({ b }: { b: BuildingSummary }) {
  return (
    <section aria-labelledby="sources-heading" className="space-y-3">
      <h2 id="sources-heading" className="font-serif text-xl font-semibold">
        Sources
      </h2>
      <ul className="divide-y divide-line rounded-lg border border-line bg-card text-sm">
        {b.sources.map((s) => (
          <li key={s.dataset} className="flex flex-col gap-1 px-4 py-3 sm:flex-row sm:justify-between">
            <span className="font-medium">{datasetTitle(s.dataset)}</span>
            <span className="text-muted">
              Imported {formatAge(s.lastImportedAt)} ({formatTimestamp(s.lastImportedAt)}) · City file updated{" "}
              {formatDate(s.sourceVersion)}
            </span>
          </li>
        ))}
      </ul>
      <p className="text-sm text-muted">
        City of Toronto Open Data. The City&apos;s &quot;updated&quot; date shows when its file changed, not that every
        record in it is current.
      </p>
    </section>
  );
}
