import { appendFile, stat } from "node:fs/promises";
import path from "node:path";
import { NextResponse, type NextRequest } from "next/server";
import { cspReportLine } from "../../../lib/csp";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const MAX_BODY = 16_384;
const MAX_LOG = 1_048_576;  // a page that keeps reporting cannot fill the disk
// `npm --prefix apps/web run start` runs here in apps/web; the log sits with the scheduler's, in the repository's logs folder.
const LOG = path.resolve(process.cwd(), "..", "..", "logs", "csp-report.log");

/** Reports from the browser about what the Content-Security-Policy would block; one short line each, nothing personal. */
export async function POST(request: NextRequest) {
  const text = await request.text().catch(() => "");
  if (text.length <= MAX_BODY) {
    let body: unknown = null;
    try { body = JSON.parse(text); } catch { /* not a report */ }
    const line = cspReportLine(body, new Date().toISOString());
    if (line && process.env.NODE_ENV === "production") {  // next dev (the browser tests) keeps nothing
      try {
        const size = await stat(LOG).then((s) => s.size, () => 0);
        if (size < MAX_LOG) await appendFile(LOG, line + "\n", "utf8");
      } catch { /* the logs folder is missing (tests): nothing to keep */ }
    }
  }
  return new NextResponse(null, { status: 204, headers: { "Cache-Control": "no-store" } });
}
