import { expect, it } from "vitest";
import { axisDomain, type BandWindow, zoneCounts } from "./percentile-bands";

const win = (over: Partial<BandWindow>): BandWindow => ({
  label: "3 năm", years: 3, weeks: 157, empty_weeks: 0, from: "2023-11-10", bases: { "năm": 157 }, reason: null,
  p: { p10: "1.00", p20: "1.10", p50: "1.30", p70: "1.50", p80: "1.60", p95: "1.80" }, min: "0.90", max: "2.00",
  mean: "1.32", sd: "0.20", skew: "0.10", z: "0.40", rank: 60, ...over,
});

it("the axis runs from the lowest week to the highest P95 or today's value, whichever is further", () => {
  expect(axisDomain([win({}), win({ min: "0.80", p: { ...win({}).p!, p95: "2.10" } })], "1.20")).toEqual([0.8, 2.1]);
  expect(axisDomain([win({})], "2.50")).toEqual([0.9, 2.5]);
  expect(axisDomain([win({ reason: "Chuỗi chỉ có từ 01/2023, chưa đủ 5 năm", p: null, min: null, max: null })], "1.20")).toBeNull();
});

it("counts the drawn windows where today is at or below P20 and at or below P10", () => {
  const windows = [win({}), win({ p: { ...win({}).p!, p20: "1.30", p10: "1.25" } }), win({ reason: "x", p: null })];
  expect(zoneCounts(windows, "1.25")).toEqual({ drawn: 2, p20: 1, p10: 1 });
  expect(zoneCounts(windows, null)).toEqual({ drawn: 2, p20: 0, p10: 0 });
});
