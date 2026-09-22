import type { Metadata } from "next";
import { connection } from "next/server";
import { api } from "@/lib/api/server";
import {
  COVERAGE_NOTES,
  formatAge,
  formatDate,
  formatTimestamp,
  LICENCE,
  NO_RECORD_IS_NOT_NO_ISSUE,
  plural,
} from "@/lib/copy/wording";

export const metadata: Metadata = { title: "About the data" };

export default async function AboutData() {
  await connection(); // freshness must be read per request, never frozen at build time
  const status = await api.dataSources();

  return (
    <div className="mx-auto max-w-3xl space-y-10">
      <header className="space-y-3">
        <h1 className="font-serif text-4xl font-semibold tracking-tight">About the data</h1>
        <p className="text-lg text-muted">
          LeaseLens combines public City of Toronto records. It organizes them. It doesn&apos;t rate buildings or
          landlords.
        </p>
      </header>

      <section aria-labelledby="datasets" className="space-y-3">
        <h2 id="datasets" className="font-serif text-2xl font-semibold">
          Datasets
        </h2>
        <ul className="divide-y divide-line rounded-lg border border-line bg-card">
          {status.datasets.map((d) => (
            <li key={d.dataset} className="space-y-1 px-4 py-4">
              <a href={d.portalUrl} className="font-medium underline underline-offset-4 hover:text-accent">
                {d.title}
              </a>
              <p className="text-sm text-muted">
                {d.lastSuccessfulImport ? (
                  <>
                    Imported {formatAge(d.lastSuccessfulImport.importedAt)} (
                    {formatTimestamp(d.lastSuccessfulImport.importedAt)})
                    {d.lastSuccessfulImport.recordCount !== null &&
                      ` · ${plural(d.lastSuccessfulImport.recordCount, "record")} in the City file`}
                    {` · City file updated ${formatDate(d.lastSuccessfulImport.sourceVersion)}`}
                  </>
                ) : (
                  "Not imported yet."
                )}
                {!d.updatedByCity && " · Archive: the City no longer updates this file."}
              </p>
              {d.lastAttempt && d.lastAttempt.status === "failed" && (
                <p className="text-sm text-note-ink">
                  The most recent update attempt failed; the data shown is from the last successful import.
                </p>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="limits" className="space-y-4">
        <h2 id="limits" className="font-serif text-2xl font-semibold">
          What these records can&apos;t tell you
        </h2>
        <ul className="list-disc space-y-3 pl-5">
          <li>
            <strong>Coverage.</strong> RentSafeTO covers purpose-built rental apartment buildings with 3 or more
            storeys and 10 or more units. Condominiums, townhouses and rentals in houses aren&apos;t included.
          </li>
          <li>
            <strong>{COVERAGE_NOTES.BUILDING_NOT_UNIT.title}.</strong> {COVERAGE_NOTES.BUILDING_NOT_UNIT.body}
          </li>
          <li>
            <strong>{COVERAGE_NOTES.SCORING_SYSTEM_CHANGED.title}.</strong> {COVERAGE_NOTES.SCORING_SYSTEM_CHANGED.body}
          </li>
          <li>
            <strong>Permits are matched by address.</strong> A permit filed under a different address for the same
            property may be missing. Permits at an address shared by several buildings aren&apos;t shown for any of
            them.
          </li>
          <li>
            <strong>Investigations and orders aren&apos;t included.</strong> The City&apos;s Investigation Activity
            application covers the past two years and includes investigations where no violation was found. Check it
            directly on the City&apos;s website.
          </li>
          <li>
            <strong>Freshness.</strong> &quot;Imported&quot; is when LeaseLens last loaded a file. The City&apos;s
            &quot;updated&quot; date shows when its file changed, not that every record in it is current.
          </li>
        </ul>
        <p className="font-medium">{NO_RECORD_IS_NOT_NO_ISSUE}</p>
      </section>

      <section aria-labelledby="licence" className="space-y-2">
        <h2 id="licence" className="font-serif text-2xl font-semibold">
          Licence
        </h2>
        <p className="text-muted">{LICENCE}</p>
      </section>
    </div>
  );
}
