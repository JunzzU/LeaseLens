import type { SearchResult } from "@/lib/api/client";
import { formatAddress } from "@/lib/copy/wording";

/** The details that tell one candidate building from another. */
export function ResultMeta({ result: r, showRsn }: { result: SearchResult; showRsn: boolean }) {
  const parts = [
    r.matchedAddress !== r.address ? `Matched ${formatAddress(r.matchedAddress)}` : null,
    r.wardName,
    r.storeys ? `${r.storeys} storeys` : null,
    r.units ? `${r.units} units` : null,
    showRsn ? `RSN ${r.rsn}` : null,
    r.rentSafeRegistered ? null : "Not in current registration",
  ].filter(Boolean);
  return <div className="text-sm text-muted">{parts.join(" · ")}</div>;
}
