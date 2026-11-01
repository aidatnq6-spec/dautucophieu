import { expect, it } from "vitest";
import { canHold, conditionParams, stateText } from "./thesis-view";

it("offers Giữ tiếp for a condition shown broken unless a hold is still in force", () => {
  const broken = { status: "broken", view: { state: "broken" as const, reading: null, reason: null }, hold: null };
  expect(canHold(broken, "2026-11-02")).toBe(true);
  expect(canHold({ ...broken, status: null }, "2026-11-02")).toBe(true);  // shown broken from stored data, not yet recorded
  expect(canHold({ ...broken, hold: { until: "2026-11-03", reason: "x" } }, "2026-11-02")).toBe(false);  // in force before its date
  expect(canHold({ ...broken, hold: { until: "2026-11-02", reason: "x" } }, "2026-11-02")).toBe(true);  // due on the review date
  expect(canHold({ ...broken, hold: { until: "2026-11-01", reason: "x" } }, "2026-11-02")).toBe(true);  // expired
  expect(canHold({ ...broken, status: "ok", view: { state: "ok" as const, reading: null, reason: null } }, "2026-11-02")).toBe(false);
});

it("reads condition parameters the Vietnamese way and refuses what the server would", () => {
  expect(conditionParams(["pct"], { pct: "10" })).toEqual({ pct: "10" });
  expect(conditionParams(["pct"], { pct: "12,5" })).toEqual({ pct: "12.5" });
  expect(conditionParams(["pct"], { pct: "0" })).toBeNull();
  expect(conditionParams(["pct"], { pct: "95" })).toBeNull();
  expect(conditionParams(["level"], { level: "48,5" })).toEqual({ level: "48.5" });
  expect(conditionParams(["level"], { level: "1.800" })).toEqual({ level: "1800" });
  expect(conditionParams(["n"], { n: "3" })).toEqual({ n: 3 });
  expect(conditionParams(["n"], { n: "3,5" })).toBeNull();
  expect(conditionParams([], {})).toEqual({});
});

it("names each state and when a broken condition was first seen", () => {
  expect(stateText({ state: "ok", reading: "giá 50", reason: null }, null)).toEqual({ text: "Đạt", tone: "good" });
  expect(stateText({ state: "broken", reading: "x", reason: null }, "2026-11-02")).toEqual({ text: "Bị phá từ 02/11/2026", tone: "bad" });
  expect(stateText({ state: "broken", reading: "x", reason: null }, null)).toEqual({ text: "Bị phá", tone: "bad" });
  expect(stateText({ state: "unknown", reading: null, reason: "Chưa có F-Score" }, null)).toEqual({ text: "Chưa kiểm được", tone: "warn" });
});
