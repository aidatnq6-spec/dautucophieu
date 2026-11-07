import { expect, it } from "vitest";
import { cell, checkLines, lastN, periodLabel } from "./financial-tables";

it("money is shown in tỷ đồng, growth with its sign, margins and returns as percentages, multiples with an x", () => {
  expect(cell("62214200000000", "money", "revenue")).toBe("62.214");
  expect(cell("-50291700000000", "money", "cogs")).toBe("-50.292");
  expect(cell("0.7088", "pct", "revenue_yoy")).toBe("+70,9%");
  expect(cell("-0.0920", "pct", "revenue_yoy")).toBe("-9,2%");
  expect(cell("0.1916", "pct", "gross_margin")).toBe("19,2%");
  expect(cell("13.14", "x", "pe")).toBe("13,1x");
  expect(cell(null, "money", "ebitda")).toBe("—");
  expect(cell("-400000000", "money", "associates")).toBe("0");  // under half a tỷ: rounds to 0, never "-0"
});

it("periods read as the screenshots do and the last n are kept", () => {
  expect(periodLabel("2026-Q3")).toBe("Q3/26");
  expect(periodLabel("2025")).toBe("2025");
  expect(lastN(["a", "b", "c"], 2)).toEqual([1, 2]);
  expect(lastN(["a", "b", "c"], 0)).toEqual([0, 1, 2]);
});

it("cross-checks are gathered into one line per period, newest first", () => {
  const checks = [
    { period: "2019", check: "capex", label: "Capex: tổng 4 quý ≠ cả năm", a: "-21622000000000", b: "-20825000000000" },
    { period: "2019", check: "cfo", label: "Lưu chuyển tiền từ HĐKD: tổng 4 quý ≠ cả năm", a: "8354000000000", b: "7715000000000" },
    { period: "2025-Q2", check: "vnstock_npat", label: "LNST công ty mẹ: VNDirect ≠ Vnstock", a: "4256000000000", b: "4300000000000" },
  ];
  expect(checkLines(checks)).toEqual([
    "Q2/25 · LNST công ty mẹ: VNDirect ≠ Vnstock (4.256 so với 4.300 tỷ)",
    "2019 · Capex: tổng 4 quý ≠ cả năm (-21.622 so với -20.825 tỷ); Lưu chuyển tiền từ HĐKD: tổng 4 quý ≠ cả năm (8.354 so với 7.715 tỷ)",
  ]);
});
