import "server-only";
import { randomBytes, randomUUID } from "node:crypto";
import { NextResponse, type NextRequest } from "next/server";
import { CSRF_COOKIE, SESSION_COOKIE, SessionError, assertMutation, assertRequestOrigin, verifyOwnerSession, type SessionAuth, type SessionConfig } from "./session";
import { signInternalRequest } from "./python-client";
import { apiError } from "./session-handlers";

// Only business areas reach Python; identity and health stay on their own routes.
const AREAS = new Set(["profile", "risk", "ledger", "universe", "valuation", "overview", "research", "jobs", "reports", "notifications", "settings", "watchlist", "market", "macro", "trend", "fairvalue", "insights", "concentration", "performance", "events", "journal", "equity-budget"]);
const SEGMENT = /^[A-Za-z0-9_-][A-Za-z0-9_.-]{0,127}$/;
const MAX_BODY = 1_048_576;

type BridgeConfig = { origin: string; token: string; hmacSecret: string };

function noStore(response: NextResponse) {
  response.headers.set("Cache-Control", "no-store");
  return response;
}

export async function proxyInternal(request: NextRequest, segments: string[], auth: SessionAuth, config: SessionConfig, bridge: BridgeConfig,
  fetcher: typeof fetch = fetch) {
  if (!segments.length || !AREAS.has(segments[0]) || segments.some((s) => !SEGMENT.test(s) || s === "." || s === "..")) {
    return noStore(NextResponse.json({ code: "not_found", message: "Không tìm thấy." }, { status: 404 }));
  }
  const method = request.method;
  let body = "";
  try {
    if (method === "GET") {
      assertRequestOrigin(request, config);
    } else {
      assertMutation(request, request.cookies.get(CSRF_COOKIE)?.value, config);
      if (request.headers.get("content-type")?.split(";")[0] !== "application/json") throw new SessionError(400, "invalid_request", "Yêu cầu không hợp lệ.");
      body = await request.text();
      if (body.length > MAX_BODY) throw new SessionError(413, "request_too_large", "Yêu cầu quá lớn.");
    }
    const owner = await verifyOwnerSession(request.cookies.get(SESSION_COOKIE)?.value, auth, config);
    const target = "/internal/" + segments.join("/");
    const headers = signInternalRequest(bridge, { uid: owner.uid, method, target, body, timestamp: Math.floor(Date.now() / 1000),
      nonce: randomBytes(16).toString("hex"), correlationId: randomUUID() });
    let upstream: Response;
    try {
      upstream = await fetcher(bridge.origin + target, { method, headers: body ? { ...headers, "content-type": "application/json" } : headers,
        body: body || undefined, cache: "no-store", redirect: "error", signal: AbortSignal.timeout(15000) });
    } catch { throw new SessionError(502, "bridge_unavailable", "Dịch vụ nội bộ chưa sẵn sàng."); }
    let data: unknown;
    try { data = await upstream.json(); } catch { throw new SessionError(502, "bridge_unavailable", "Dịch vụ nội bộ trả dữ liệu không hợp lệ."); }
    return noStore(NextResponse.json(data, { status: upstream.status }));
  } catch (error) { return apiError(error); }
}
