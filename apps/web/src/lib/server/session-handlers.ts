import "server-only";
import { randomBytes } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { CSRF_COOKIE, SESSION_COOKIE, SessionError, assertMutation, assertRequestOrigin, cookieOptions, createOwnerSession, verifyOwnerSession, type SessionAuth, type SessionConfig } from "./session";

export function apiError(error: unknown) {
  const safe = error instanceof SessionError ? error : new SessionError(503, "auth_unavailable", "Dịch vụ xác thực chưa sẵn sàng.");
  return NextResponse.json({ code: safe.code, message: safe.message }, { status: safe.status, headers: { "Cache-Control": "no-store" } });
}
function json(value: unknown) { return NextResponse.json(value, { headers: { "Cache-Control": "no-store" } }); }

export function sessionHandlers(getAuth: () => SessionAuth, getConfig: () => SessionConfig) {
  return {
    async csrf(request: NextRequest) {
      try {
        const config = getConfig();
        assertRequestOrigin(request, config);
        if ((request.headers.get("origin") && request.headers.get("origin") !== config.origin) || request.headers.get("sec-fetch-site") === "cross-site") throw new SessionError(403, "invalid_origin", "Nguồn yêu cầu không hợp lệ.");
        const csrfToken = randomBytes(32).toString("hex");
        const response = json({ csrfToken });
        response.cookies.set(CSRF_COOKIE, csrfToken, { ...cookieOptions(config), sameSite: "strict", maxAge: 3600 });
        return response;
      } catch (error) { return apiError(error); }
    },
    async login(request: NextRequest) {
      try {
        const config = getConfig();
        assertMutation(request, request.cookies.get(CSRF_COOKIE)?.value, config);
        if (request.headers.get("content-type")?.split(";")[0] !== "application/json") throw new SessionError(400, "invalid_request", "Yêu cầu đăng nhập không hợp lệ.");
        const text = await request.text();
        if (text.length > 20000) throw new SessionError(400, "invalid_request", "Yêu cầu đăng nhập không hợp lệ.");
        let data: unknown;
        try { data = JSON.parse(text); } catch { throw new SessionError(400, "invalid_request", "Yêu cầu đăng nhập không hợp lệ."); }
        if (!data || typeof data !== "object" || !("idToken" in data) || typeof data.idToken !== "string") throw new SessionError(400, "invalid_request", "Yêu cầu đăng nhập không hợp lệ.");
        const cookie = await createOwnerSession(data.idToken, getAuth(), config);
        const response = json({ status: "authenticated" });
        response.cookies.set(SESSION_COOKIE, cookie, cookieOptions(config));
        return response;
      } catch (error) { return apiError(error); }
    },
    async logout(request: NextRequest) {
      let config: SessionConfig;
      try {
        config = getConfig();
        assertMutation(request, request.cookies.get(CSRF_COOKIE)?.value, config);
      } catch (error) { return apiError(error); }
      let response: NextResponse;
      try {
        const auth = getAuth();
        const owner = await verifyOwnerSession(request.cookies.get(SESSION_COOKIE)?.value, auth, config);
        await auth.revokeRefreshTokens(owner.uid);
        response = json({ status: "signed_out" });
      } catch (error) { response = apiError(error); }
      response.cookies.set(SESSION_COOKIE, "", { ...cookieOptions(config), maxAge: 0 });
      response.cookies.set(CSRF_COOKIE, "", { ...cookieOptions(config), sameSite: "strict", maxAge: 0 });
      return response;
    },
  };
}
