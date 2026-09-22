# LeaseLens Toronto — website

Next.js 16 (App Router, TypeScript, Tailwind CSS 4). Pages are server-rendered from the LeaseLens API. Address suggestions are fetched from the browser as you type.

```bash
npm install
cp .env.example .env.local        # API URLs; defaults point at http://localhost:8080
npm run dev                        # http://localhost:3000 (the backend must be running)
```

| Script | |
|---|---|
| `npm run gen:api` | Regenerate `lib/api/schema.d.ts` from the running backend's OpenAPI description |
| `npm test` | Unit tests (vitest) |
| `npm run typecheck` / `npm run lint` | TypeScript and ESLint |
| `npm run build` | Production build |

## Layout

```
app/            pages: / · /search · /buildings/[id] · /about-data
components/     SearchBox (address suggestions, ARIA combobox) · ResultMeta
lib/api/        generated API types + a plain fetch client (no Next.js imports)
lib/copy/       everything the site says to a renter, as plain functions
```

`lib/api` and `lib/copy` are deliberately framework-free, so the planned mobile app can reuse them.

## Wording rules

The site describes public records and never judges a building. There's no "safe/unsafe", and scores are never colour-coded good or bad. It says what's missing, and that "no record found" doesn't mean "no issue". A unit test fails if a coverage note uses verdict words. The wording comes from [`docs/limitations.md`](../docs/limitations.md).
