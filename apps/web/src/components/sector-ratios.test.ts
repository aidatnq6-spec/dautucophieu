import { expect, it } from "vitest";
import { chartRows } from "./sector-ratios";

it("sector ratios become chart rows: quarters as periods, percentages as pct and times as multiples, gaps kept", () => {
  const view = {
    symbol: "MBB", kind: "bank" as const,
    quarters: [{ date: "2026-06-30", label: "Q2/2026" }, { date: "2026-09-30", label: "Q3/2026" }],
    metrics: [{ code: "BAD_LOANS_RATIO_AQ", label: "Tỷ lệ nợ xấu (NPL)", format: "pct2" as const, values: ["0.0144", "0.0166"] },
      { code: "LOANS_TO_EQUITY_AQ", label: "Cho vay / vốn chủ", format: "times" as const, values: [null, "0.97"] }],
  };
  const { periods, rows } = chartRows(view);
  expect(periods).toEqual(["2026-Q2", "2026-Q3"]);
  expect(rows).toEqual([
    { key: "BAD_LOANS_RATIO_AQ", label: "Tỷ lệ nợ xấu (NPL)", kind: "pct", indent: 0, values: ["0.0144", "0.0166"] },
    { key: "LOANS_TO_EQUITY_AQ", label: "Cho vay / vốn chủ", kind: "x", indent: 0, values: [null, "0.97"] },
  ]);
});
