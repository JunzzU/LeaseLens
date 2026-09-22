import type { Metadata } from "next";
import Link from "next/link";
import { ResultMeta } from "@/components/ResultMeta";
import { SearchBox } from "@/components/SearchBox";
import { api } from "@/lib/api/server";
import { describeSearch, formatAddress, NO_MATCH_HELP } from "@/lib/copy/wording";

export const metadata: Metadata = { title: "Search" };

/** Full results for a query; what Enter opens, and what works without JavaScript. */
export default async function SearchPage({ searchParams }: PageProps<"/search">) {
  const raw = (await searchParams).q;
  const q = (Array.isArray(raw) ? raw[0] : raw)?.trim() ?? "";
  const response = q ? await api.search(q, 20) : null;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <SearchBox initialQuery={q} />
      {!response ? (
        <p className="text-muted">Enter a street address to search.</p>
      ) : (
        <section aria-labelledby="results-heading" className="space-y-3">
          <h1 id="results-heading" className="text-lg font-medium">
            {describeSearch(response)}
          </h1>
          {response.results.length === 0 ? (
            <p className="text-muted">{NO_MATCH_HELP}</p>
          ) : (
            <ul className="divide-y divide-line overflow-hidden rounded-lg border border-line bg-card">
              {response.results.map((r) => (
                <li key={r.buildingId}>
                  <Link href={`/buildings/${r.buildingId}`} className="block px-4 py-3 hover:bg-accent-soft">
                    <div className="font-medium">{formatAddress(r.address)}</div>
                    <ResultMeta result={r} showRsn={response.ambiguous} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
          {response.hasMore && <p className="text-sm text-muted">More buildings match. Add more of the address to narrow the list.</p>}
        </section>
      )}
    </div>
  );
}
