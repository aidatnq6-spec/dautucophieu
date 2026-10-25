// @vitest-environment node
import { afterEach, expect, it, vi } from "vitest";
vi.mock("server-only", () => ({}));
import { e2eSessionAuth } from "./e2e-auth";

const TOKEN = "e".repeat(48);
afterEach(() => vi.unstubAllEnvs());

function enable(env: string) {
  vi.stubEnv("NODE_ENV", env);
  vi.stubEnv("INVESTMENT_E2E_SESSION", TOKEN);
  vi.stubEnv("FIREBASE_OWNER_UID", "owner-1");
}

it("is refused in production even when the flag is set", () => {
  enable("production");
  expect(() => e2eSessionAuth()).toThrow();
});

it("accepts only the exact test session token", async () => {
  enable("development");
  const auth = e2eSessionAuth();
  await expect(auth.verifySessionCookie(TOKEN, true)).resolves.toMatchObject({ uid: "owner-1", firebase: { sign_in_provider: "google.com" } });
  await expect(auth.verifySessionCookie("e".repeat(47) + "f", true)).rejects.toThrow();
  await expect(auth.verifyIdToken(TOKEN, true)).rejects.toThrow();
});

it("needs a long random token", () => {
  enable("development");
  vi.stubEnv("INVESTMENT_E2E_SESSION", "short");
  expect(() => e2eSessionAuth()).toThrow();
});
