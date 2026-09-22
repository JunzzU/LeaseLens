"use client";

import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";
import { createClient, type SearchResponse } from "@/lib/api/client";
import { describeSearch, formatAddress } from "@/lib/copy/wording";
import { ResultMeta } from "./ResultMeta";

const client = createClient({ baseUrl: process.env.NEXT_PUBLIC_LEASELENS_API_URL ?? "http://localhost:8080" });
const MIN_CHARS = 2;
const DEBOUNCE_MS = 200;

/**
 * Address search with suggestions (ARIA combobox pattern). Enter on a highlighted suggestion
 * opens that building; Enter otherwise opens the full results page, which also works without JS.
 */
export function SearchBox({ initialQuery = "", autoFocus = false }: { initialQuery?: string; autoFocus?: boolean }) {
  const router = useRouter();
  const listId = useId();
  const [query, setQuery] = useState(initialQuery);
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [failed, setFailed] = useState(false);
  const wrapper = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const q = query.trim();
    if (q.length < MIN_CHARS) return; // the list is hidden below MIN_CHARS, so nothing to clear
    const controller = new AbortController();
    const timer = setTimeout(() => {
      client
        .search(q, 8, controller.signal)
        .then((r) => {
          setResponse(r);
          setFailed(false);
          setActive(-1);
        })
        .catch((e) => {
          if (e.name !== "AbortError") setFailed(true);
        });
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query]);

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (!wrapper.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const results = response?.results ?? [];
  const showList = open && query.trim().length >= MIN_CHARS && (response !== null || failed);

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setActive((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, -1));
    } else if (e.key === "Escape") {
      setOpen(false);
    } else if (e.key === "Enter" && active >= 0 && results[active]) {
      e.preventDefault();
      router.push(`/buildings/${results[active].buildingId}`);
    }
  }

  return (
    <div ref={wrapper} className="relative">
      <form action="/search" role="search" className="flex gap-2">
        <label htmlFor={`${listId}-input`} className="sr-only">
          Street address
        </label>
        <input
          id={`${listId}-input`}
          name="q"
          type="text"
          inputMode="search"
          autoComplete="off"
          autoFocus={autoFocus}
          placeholder="e.g. 181 Gerrard St E"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          role="combobox"
          aria-expanded={showList}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
          className="min-w-0 flex-1 rounded-lg border border-line bg-card px-4 py-3 text-lg shadow-sm placeholder:text-muted/70"
        />
        <button type="submit" className="rounded-lg bg-accent px-5 py-3 font-medium text-accent-ink hover:opacity-90">
          Search
        </button>
      </form>

      {showList && (
        <div className="absolute z-10 mt-2 w-full overflow-hidden rounded-lg border border-line bg-card shadow-lg">
          {failed ? (
            <p className="px-4 py-3 text-sm text-muted">Search is unavailable right now. Please try again shortly.</p>
          ) : (
            <>
              <p className="border-b border-line px-4 py-2 text-sm text-muted" aria-live="polite">
                {describeSearch(response!)}
              </p>
              <ul id={listId} role="listbox" aria-label="Matching buildings">
                {results.map((r, i) => (
                  <li
                    key={r.buildingId}
                    id={`${listId}-${i}`}
                    role="option"
                    aria-selected={i === active}
                    onMouseEnter={() => setActive(i)}
                    onMouseDown={(e) => {
                      e.preventDefault();
                      router.push(`/buildings/${r.buildingId}`);
                    }}
                    className={`cursor-pointer px-4 py-3 ${i === active ? "bg-accent-soft" : ""}`}
                  >
                    <div className="font-medium">{formatAddress(r.address)}</div>
                    <ResultMeta result={r} showRsn={response!.ambiguous} />
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
}
