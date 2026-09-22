import "server-only";
import { createClient } from "./client";

/** API client for Server Components. LEASELENS_API_URL is read on the server only. */
export const api = createClient({
  baseUrl: process.env.LEASELENS_API_URL ?? "http://localhost:8080",
});
