import { expect, it } from "vitest";
import { conditionParams, stateText } from "./thesis-view";

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
