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

it("book value per share is shown in whole đồng", () => {
  expect(cell("13940", "vnd", "bvps")).toBe("13.940 đ");
  expect(cell(null, "vnd", "bvps")).toBe("—");
});

it("a financial company's quarters take its sector ratios first, over the quarters of both, gaps kept", async () => {
  const { withRatios } = await import("./financial-tables");
  const part = { periods: ["2026-Q2", "2026-Q3"], rows: [{ key: null, label: "Quy mô và định giá", kind: "group" as const, indent: 0, values: [] },
    { key: "pb", label: "P/B", kind: "x" as const, indent: 0, values: ["1.30", "1.26"] }] };
  const ratios = { kind: "bank" as const, quarters: [{ date: "2026-03-31", label: "Q1/2026" }, { date: "2026-09-30", label: "Q3/2026" }],
    metrics: [{ code: "BAD_LOANS_RATIO_AQ", label: "Tỷ lệ nợ xấu (NPL)", format: "pct2" as const, values: ["0.0142", "0.0166"] },
      { code: "LOANS_TO_EQUITY_AQ", label: "Cho vay / vốn chủ", format: "times" as const, values: [null, "0.97"] }] };
  const out = withRatios(part, ratios);
  expect(out.periods).toEqual(["2026-Q1", "2026-Q2", "2026-Q3"]);
  expect(out.rows.map((r) => [r.key, r.kind, r.values])).toEqual([
    [null, "group", []],
    ["BAD_LOANS_RATIO_AQ", "pct", ["0.0142", null, "0.0166"]],
    ["LOANS_TO_EQUITY_AQ", "x", [null, null, "0.97"]],
    [null, "group", []],
    ["pb", "x", [null, "1.30", "1.26"]],
  ]);
  expect(out.rows[0].label).toBe("Chỉ số ngân hàng");
});

it("ratios VNDirect gives to two places keep them", () => {
  expect(cell("0.0166", "pct", "BAD_LOANS_RATIO_AQ")).toBe("1,66%");
  expect(cell("0.97", "x", "LOANS_TO_EQUITY_AQ")).toBe("0,97x");
  expect(cell("0.2120", "pct", "ROAE_TR_AVG4Q")).toBe("21,2%");
});
