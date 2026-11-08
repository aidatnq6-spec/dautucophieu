import { expect, it } from "vitest";
import { axes, linePath, plotValue, scaleOf, seriesName, toggleRow } from "./statement-chart";

const rows = [
  { key: null, label: "Doanh thu", kind: "group" as const, indent: 0, values: [] },
  { key: "revenue", label: "Doanh thu thuần", kind: "money" as const, indent: 0, values: [] },
  { key: "revenue_yoy", label: "% so cùng kỳ", kind: "pct" as const, indent: 1, values: [] },
  { key: "gross_margin", label: "Biên gộp", kind: "pct" as const, indent: 1, values: [] },
  { key: "pe", label: "P/E", kind: "x" as const, indent: 0, values: [] },
];

it("clicking a row adds it, clicking again removes it, a third replaces the earliest", () => {
  expect(toggleRow([], "revenue")).toEqual(["revenue"]);
  expect(toggleRow(["revenue"], "gross_margin")).toEqual(["revenue", "gross_margin"]);
  expect(toggleRow(["revenue", "gross_margin"], "revenue")).toEqual(["gross_margin"]);
  expect(toggleRow(["revenue", "gross_margin"], "pe")).toEqual(["gross_margin", "pe"]);
});

it("a growth row is named after the line it measures", () => {
  expect(seriesName(rows, "revenue_yoy")).toBe("Doanh thu thuần · % so cùng kỳ");
  expect(seriesName(rows, "gross_margin")).toBe("Biên gộp");
  expect(seriesName(rows, "pe")).toBe("P/E");
});

it("money plots in tỷ đồng, ratios in percent, multiples as they are; a missing value stays missing", () => {
  expect(plotValue("4058000000000", "money")).toBe(4058);
  expect(plotValue("0.186", "pct")).toBeCloseTo(18.6);
  expect(plotValue("13.14", "x")).toBe(13.14);
  expect(plotValue("400000000", "money")).toBe(0);  // what the table shows: under half a tỷ is 0, so the spark draws no bar
  expect(plotValue("-2600000000", "money")).toBe(-3);
  expect(plotValue(null, "money")).toBeNull();
});

it("each unit gets its own axis, in the order the rows were picked", () => {
  expect(axes(["money", "pct"])).toEqual({ left: "money", right: "pct" });
  expect(axes(["pct", "pct"])).toEqual({ left: "pct", right: null });
  expect(axes(["money", "money"])).toEqual({ left: "money", right: null });
});

it("bars stand on zero, so their scale always holds zero; a flat line still gets a span", () => {
  expect(scaleOf([3000, 4000], true)).toEqual({ lo: 0, hi: 4000 });
  expect(scaleOf([-2000, 4000], true)).toEqual({ lo: -2000, hi: 4000 });
  expect(scaleOf([18, 25], false)).toEqual({ lo: 18, hi: 25 });
  expect(scaleOf([20, 20], false)).toEqual({ lo: 19, hi: 21 });
  expect(scaleOf([null, null], true)).toBeNull();
});

it("a missing value breaks the line instead of joining across it", () => {
  const d = linePath([1, 2, null, 4, 5], (i) => i * 10, (v) => v);
  expect(d).toBe("M0.0,1.0L10.0,2.0M30.0,4.0L40.0,5.0");
  expect(linePath([1, null, 3], (i) => i, (v) => v)).toBe("M0.0,1.0M2.0,3.0");
});
