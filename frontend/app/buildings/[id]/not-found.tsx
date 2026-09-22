import Link from "next/link";

export default function BuildingNotFound() {
  return (
    <div className="mx-auto max-w-xl space-y-4 py-12 text-center">
      <h1 className="font-serif text-3xl font-semibold">Building not found</h1>
      <p className="text-muted">There&apos;s no building with that ID in LeaseLens. The link may be out of date.</p>
      <Link href="/" className="inline-block rounded-lg bg-accent px-5 py-3 font-medium text-accent-ink">
        Search for an address
      </Link>
    </div>
  );
}
