import Link from "next/link";
import { SearchBox } from "@/components/SearchBox";

export default function Home() {
  return (
    <div className="mx-auto max-w-2xl space-y-10 py-8">
      <section className="space-y-4">
        <h1 className="font-serif text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
          Look up a Toronto apartment building before you sign.
        </h1>
        <p className="text-lg text-muted">
          City evaluations, building permits and how they&apos;ve changed over time, in one place, with the
          source and date of every record.
        </p>
      </section>

      <SearchBox autoFocus />

      <section aria-labelledby="what" className="grid gap-4 sm:grid-cols-3">
        <h2 id="what" className="sr-only">
          What you&apos;ll find
        </h2>
        {[
          ["Evaluations", "RentSafeTO inspection scores for the building's common areas, and how they've changed."],
          ["Permits", "Repairs, renovations and construction the City has permitted at the address."],
          ["Sources", "Where each record comes from, when it was last updated, and what it can't tell you."],
        ].map(([title, body]) => (
          <div key={title} className="rounded-lg border border-line bg-card p-4">
            <h3 className="font-medium">{title}</h3>
            <p className="mt-1 text-sm text-muted">{body}</p>
          </div>
        ))}
      </section>

      <p className="text-sm text-muted">
        Covers purpose-built rental buildings with 3+ storeys and 10+ units registered with the City&apos;s
        RentSafeTO program. Condos, townhouses and rentals in houses aren&apos;t included.{" "}
        <Link href="/about-data" className="underline underline-offset-4 hover:text-ink">
          About the data
        </Link>
      </p>
    </div>
  );
}
