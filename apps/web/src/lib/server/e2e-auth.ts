import "server-only";
import { timingSafeEqual } from "node:crypto";
import { SessionError, type SessionAuth } from "./session";

/**
 * Browser end-to-end tests only: accepts one random session token from the test
 * runner and never mints sessions. Refused under NODE_ENV=production, so a
 * built and started app cannot be switched into this mode.
 */
export function e2eSessionAuth(): SessionAuth {
  const token = process.env.INVESTMENT_E2E_SESSION ?? "";
  const uid = process.env.FIREBASE_OWNER_UID ?? "";
  if (process.env.NODE_ENV === "production" || !/^[\x21-\x7e]{32,}$/.test(token) || !uid) {
    throw new SessionError(503, "auth_unavailable", "Chế độ kiểm thử không được phép.");
  }
  const reject = async (): Promise<never> => { throw new SessionError(); };
  return {
    verifyIdToken: reject,
    createSessionCookie: reject,
    async verifySessionCookie(cookie) {
      const a = Buffer.from(cookie), b = Buffer.from(token);
      if (a.length !== b.length || !timingSafeEqual(a, b)) throw new SessionError();
      return { uid, auth_time: Math.floor(Date.now() / 1000), firebase: { sign_in_provider: "google.com" } };
    },
    async revokeRefreshTokens() {},
  };
}
