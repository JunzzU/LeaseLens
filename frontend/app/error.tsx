"use client";

export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="mx-auto max-w-xl space-y-4 py-12 text-center">
      <h1 className="font-serif text-3xl font-semibold">Something went wrong</h1>
      <p className="text-muted">We couldn&apos;t load this page. The data service may be briefly unavailable.</p>
      <button onClick={reset} className="rounded-lg bg-accent px-5 py-3 font-medium text-accent-ink">
        Try again
      </button>
    </div>
  );
}
