import { expect, it } from "vitest";
import { axisDomain, type BandWindow, episodeLine, presetPrice, sourceNote, zoneCounts } from "./percentile-bands";

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

it("the axis also reaches the assumed multiple", () => {
  expect(axisDomain([win({})], "1.20", "0.50")).toEqual([0.5, 1.8]);
});

it("a preset price is today's close less the percentage, rounded to 10 đồng", () => {
  expect(presetPrice("32450", 5)).toBe(30830);
  expect(presetPrice("15100", 20)).toBe(12080);
});

it("the twelve-month line names how many episodes and gives a rate only from the minimum sample", () => {
  const ep = { list: [], done: 2, pending: 1, wins: 2, win_rate: null, median: null, worst_return: "0.1000", worst_drawdown: "-0.0270", min_episodes: 5 };
  expect(episodeLine(ep)).toBe("Có lãi 2/2 đợt — chưa đủ mẫu để tính tỉ lệ (cần ít nhất 5 đợt) · 1 đợt chưa đủ 12 tháng");
  expect(episodeLine({ ...ep, done: 6, wins: 5, pending: 0, win_rate: "0.8333", median: "0.1520" }))
    .toBe("Có lãi 5/6 đợt (83%) · trung vị +15,2%");
  expect(episodeLine({ ...ep, done: 0, wins: 0, pending: 0, worst_return: null, worst_drawdown: null })).toBe("Chưa lần nào về mức này trong chuỗi");
});

it("the caption names where the quarters come from and when a report counts as out", () => {
  expect(sourceNote("vndirect")).toBe("Lợi nhuận và vốn chủ của công ty mẹ theo báo cáo VNDirect; một kỳ tính là đã công bố từ ngày VNDirect đưa số lên nếu trong 120 ngày sau khi hết kỳ, nếu không thì 45 ngày sau khi hết quý, năm từ 1/4 năm sau.");
  expect(sourceNote("vnstock")).toBe("Số liệu Vnstock (8 kỳ gần nhất); quý tính là đã công bố 45 ngày sau khi hết quý, năm từ 1/4 năm sau.");
});
