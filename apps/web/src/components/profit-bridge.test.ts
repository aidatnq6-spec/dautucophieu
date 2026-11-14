import { describe, expect, it } from "vitest";
import { profitBars, profitNotes } from "./profit-bridge";

const b = { status: "ok" as const, quarter: "2026-Q3", base_quarter: "2025-Q3", start: "180000000000", end: "193000000000", margins: { base: "4000", now: "3500" },
  steps: [{ id: "revenue", amount: "80000000000" }, { id: "margin", amount: "-60000000000" }, { id: "selling", amount: "-10000000000" },
    { id: "financial", amount: "0" }, { id: "minority", amount: "10000000000" }], other: "3000000000" };

describe("profit bridge", () => {
  it("runs from last year to this quarter, drops zero steps and shows the unexplained gap on its own", () => {
    expect(profitBars(b).map((x) => x.label)).toEqual(["Q3/2025", "Doanh thu", "Biên gộp", "Chi phí bán hàng", "Cổ đông thiểu số", "Khác (chưa khớp dòng)", "Q3/2026"]);
  });
  it("names the two largest pushes each way", () => {
    expect(profitNotes(b)).toEqual(["Doanh thu kéo lên 80,0 tỷ", "Cổ đông thiểu số kéo lên 10,0 tỷ", "Biên gộp kéo xuống 60,0 tỷ", "Chi phí bán hàng kéo xuống 10,0 tỷ"]);
  });
});
