import { expect, it } from "vitest";
import { cell, lastN, periodLabel } from "./financial-tables";

it("money is shown in tỷ đồng, growth with its sign, margins and returns as percentages, multiples with an x", () => {
  expect(cell("62214200000000", "money", "revenue")).toBe("62.214");
  expect(cell("-50291700000000", "money", "cogs")).toBe("-50.292");
  expect(cell("0.7088", "pct", "revenue_yoy")).toBe("+70,9%");
  expect(cell("-0.0920", "pct", "revenue_yoy")).toBe("-9,2%");
  expect(cell("0.1916", "pct", "gross_margin")).toBe("19,2%");
  expect(cell("13.14", "x", "pe")).toBe("13,1x");
  expect(cell(null, "money", "ebitda")).toBe("—");
});

it("periods read as the screenshots do and the last n are kept", () => {
  expect(periodLabel("2026-Q3")).toBe("Q3/26");
  expect(periodLabel("2025")).toBe("2025");
  expect(lastN(["a", "b", "c"], 2)).toEqual([1, 2]);
  expect(lastN(["a", "b", "c"], 0)).toEqual([0, 1, 2]);
});
