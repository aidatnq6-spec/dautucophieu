import "server-only";
import { createHash, createHmac, randomBytes, randomUUID } from "node:crypto";
import type { NextRequest } from "next/server";
import { SESSION_COOKIE, SessionError, assertRequestOrigin, verifyOwnerSession, type SessionAuth, type SessionConfig } from "./session";

type BridgeConfig = { origin: string; token: string; hmacSecret: string };
function validateBridge(config: BridgeConfig) {
  const secret = /^[\x21-\x7e]{32,}$/;
  if (!secret.test(config.token) || !secret.test(config.hmacSecret) || config.token === config.hmacSecret) throw new SessionError(503, "bridge_unavailable", "Chưa cấu hình xác thực nội bộ.");
  let url: URL;
  try { url = new URL(config.origin); } catch { throw new SessionError(503, "bridge_unavailable", "Địa chỉ dịch vụ nội bộ không hợp lệ."); }
  if (url.origin !== config.origin || url.hostname !== "127.0.0.1" || url.protocol !== "http:") throw new SessionError(503, "bridge_unavailable", "Địa chỉ dịch vụ nội bộ không hợp lệ.");
}
export function bridgeConfig(): BridgeConfig {
  const config = { origin: process.env.PYTHON_API_ORIGIN ?? "http://127.0.0.1:8000", token: process.env.INTERNAL_API_TOKEN ?? "", hmacSecret: process.env.INTERNAL_API_HMAC_SECRET ?? "" };
  validateBridge(config);
  return config;
}

export function signInternalRequest(config: BridgeConfig, input: { uid: string; method: string; target: string; body: string; timestamp: number; nonce: string; correlationId: string }): Record<string, string> {
  validateBridge(config);
  const digest = createHash("sha256").update(input.body, "utf8").digest("hex");
  const canonical = ["v1", String(input.timestamp), input.nonce, input.uid, "owner", input.correlationId, input.method, input.target, digest].join("\n");
  return {
    authorization: `Bearer ${config.token}`, "x-owner-uid": input.uid, "x-owner-role": "owner",
    "x-correlation-id": input.correlationId, "x-request-timestamp": String(input.timestamp),
    "x-request-nonce": input.nonce, "x-request-signature": createHmac("sha256", config.hmacSecret).update(canonical, "utf8").digest("hex"),
  };
}

export async function proxyIdentity(request: NextRequest, auth: SessionAuth, config: SessionConfig, bridge: BridgeConfig, fetcher: typeof fetch = fetch) {
  assertRequestOrigin(request, config);
  const owner = await verifyOwnerSession(request.cookies.get(SESSION_COOKIE)?.value, auth, config);
  validateBridge(bridge);
  const target = "/internal/identity";
  const headers = signInternalRequest(bridge, { uid: owner.uid, method: "GET", target, body: "", timestamp: Math.floor(Date.now() / 1000), nonce: randomBytes(16).toString("hex"), correlationId: randomUUID() });
  try {
    const response = await fetcher(bridge.origin + target, { method: "GET", headers, cache: "no-store", redirect: "error", signal: AbortSignal.timeout(5000) });
    if (!response.ok) throw new Error();
    const data: unknown = await response.json();
    if (!data || typeof data !== "object" || !("uid" in data) || data.uid !== owner.uid || !("role" in data) || data.role !== "owner" || !("correlation_id" in data) || typeof data.correlation_id !== "string") throw new Error();
    return { uid: owner.uid, role: owner.role, correlation_id: data.correlation_id };
  } catch { throw new SessionError(502, "bridge_unavailable", "Dịch vụ nội bộ chưa sẵn sàng."); }
}
