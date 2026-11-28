import { expect, it } from "vitest";
import { cell, checkLines, epsNote, fixedNotes, historyCards, lastN, outsideSalesNote, periodLabel, sectorColumn, sectorNote, showsSector, withRatios } from "./financial-tables";

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
  expect(cell("0.0170", "pct", "GROUP2_RATIO")).toBe("1,70%");  // the owner's group-2 share to two places, as NPL beside it
  expect(cell("0.3300", "pct", "CASA")).toBe("33,0%");
  expect(cell("0.1461", "pct", "CAR")).toBe("14,61%");  // year-end CAR to two places, as the banks report it
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

it("the fixed-asset group says when a ticker has not taken its lines yet and where a finance lease has no line of its own", () => {
  expect(fixedNotes({ fixed_assets_pending: true, finance_lease: [] })).toEqual(["Chưa đồng bộ dòng tài sản cố định, chi phí trả trước, lợi thế thương mại, nợ vay, vốn chủ sở hữu, thuế TNDN và trái phiếu chuyển đổi: các dòng này để trống đến lượt 20:00 lấy lại lịch sử của mã này."]);
  expect(fixedNotes({ fixed_assets_pending: false, finance_lease: ["2024", "2025-Q1"] })).toEqual(["Có TSCĐ thuê tài chính (không có dòng riêng) ở 2024, Q1/25."]);
  expect(fixedNotes({})).toEqual([]);
});

it("VNDirect's ratios of a general company read in days, times and percentages, as the first group of the quarters", () => {
  expect(cell("61.4", "days", "DSO_TR_AVG5Q")).toBe("61 ngày");
  expect(cell("-1", "days", "DSO_TR_AVG5Q")).toBe("-1 ngày");
  const part = withRatios({ periods: ["2026-Q2", "2026-Q3"], rows: [{ key: "revenue", label: "Doanh thu", kind: "money", indent: 0, values: ["1", "2"] }] },
    { kind: "general", quarters: [{ date: "2026-09-30", label: "Q3/2026" }],
      metrics: [{ code: "ROAE_TR_AVG4Q", label: "ROAE", format: "pct1", values: ["0.28"] }, { code: "DSO_TR_AVG5Q", label: "Số ngày phải thu", format: "days", values: ["61.4"] }] });
  expect(part.rows[0].label).toBe("Chỉ số tài chính (VNDirect)");
  expect(part.rows.map((r) => r.kind)).toEqual(["group", "pct", "days", "money"]);
  expect(part.rows[1].values).toEqual([null, "0.28"]);
});

it("profit mostly outside sales and an EPS far from profit are said in words, only past the owner's thresholds", () => {
  const flag = (q: string | null, qv: boolean | null, f: string | null, fv: boolean | null) => ({ nguong: "0.3",
    quy_gan_nhat: { ky: "2026-Q3", ty_le: q, vuot_nguong: qv }, bon_quy: { ky: ["2025-Q4", "2026-Q1", "2026-Q2", "2026-Q3"], ty_le: f, vuot_nguong: fv } });
  expect(outsideSalesNote(flag("0.686", true, "0.5736", true))).toBe("Lợi nhuận ngoài bán hàng: doanh thu tài chính và lợi nhuận khác bằng 68,6% LNTT Q3/2026, "
    + "57,4% LNTT 4 quý đến Q3/2026 (ngưỡng 30%). Lãi tiền gửi đều đặn cũng nằm trong doanh thu tài chính, nên đây không hẳn là khoản một lần.");
  expect(outsideSalesNote(flag("0.25", false, "0.41", true))).toContain("bằng 41% LNTT 4 quý đến Q3/2026 (ngưỡng 30%)");
  expect(outsideSalesNote(flag("0.25", false, null, null))).toBeNull();
  expect(outsideSalesNote(null)).toBeNull();
  expect(epsNote([{ nam: "2017" }, { nam: "2024" }, { nam: "2025" }])).toBe("EPS lệch hẳn LNST công ty mẹ năm 2017, 2024, 2025 (hơn 3 lần so năm trước): "
    + "có thể là lỗi nguồn hoặc phát hành nhiều cổ phiếu; số giữ nguyên như VNDirect.");
  expect(epsNote([])).toBeNull();
});

it("the sector column carries the medians of VNDirect's rows for the ticker's own quarter, and nothing without a sector", () => {
  const col = sectorColumn({ name: "Bất động sản", quarter: "2026-09-30", peers: 58, medians: { ROAE_TR_AVG4Q: "0.0466", DSO_TR_AVG5Q: null }, counts: {} });
  expect(col).toEqual({ label: "Trung vị ngành Q3/26", values: { ROAE_TR_AVG4Q: "0.0466", DSO_TR_AVG5Q: null } });
  expect(sectorColumn(null)).toBeNull();
  expect(sectorColumn(undefined)).toBeNull();
});

it("P/E and P/B are set against the ticker's own 3- and 5-year medians, only where a median exists", () => {
  const cards = historyCards({ date: "2026-11-06", pe: { now: "10.98", median_3y: "37.02", median_5y: "28.23", lower_3y: "2/37" },
    pb: { now: "0.99", median_3y: "1.79", median_5y: null, lower_3y: "1/37" } });
  expect(cards).toEqual([
    { title: "P/E so với lịch sử (06/11/2026)", value: "11,0x · 3 năm 37,0x · 5 năm 28,2x", sub: "2/37 tháng trong 3 năm thấp hơn" },
    { title: "P/B so với lịch sử (06/11/2026)", value: "0,99x · 3 năm 1,79x · 5 năm —", sub: "1/37 tháng trong 3 năm thấp hơn" }]);
  expect(historyCards(null)).toEqual([]);
  expect(historyCards({ date: "2026-11-06", pe: null, pb: null })).toEqual([]);
});

it("the sector median column shows for general companies and banks only", () => {
  expect(showsSector("general")).toBe(true);
  expect(showsSector("bank")).toBe(true);
  expect(showsSector("securities")).toBe(true);  // against the other investment-services firms (27/11/2026)
  expect(showsSector("insurance")).toBe(true);  // against the other HOSE insurers, life and non-life together (27/11/2026)
  expect(showsSector(undefined)).toBe(false);
});

it("the median note names the peers and quarter, and for a bank why CASA and nhóm 2 have none", () => {
  const sector = { name: "Ngân hàng", quarter: "2026-09-30", peers: 21, medians: {}, counts: {} };
  const bank = sectorNote({ kind: "bank", sector })!;
  expect(bank).toContain("trung vị của 21 doanh nghiệp cùng ngành Ngân hàng (ICB cấp 2, HOSE) có số ở quý Q3/26");
  expect(bank).toContain("CASA và tỷ lệ nợ nhóm 2 không có trung vị");
  expect(sectorNote({ kind: "general", sector: { ...sector, name: "Bất động sản" } })).not.toContain("CASA");
  const broker = sectorNote({ kind: "securities", sector: { ...sector, name: "Dịch vụ đầu tư (chứng khoán)", peers: 20 } })!;
  expect(broker).toContain("trung vị của 20 doanh nghiệp cùng ngành Dịch vụ đầu tư (chứng khoán) (ICB cấp 4, HOSE)");
  expect(broker).not.toContain("CASA");
  const insurer = sectorNote({ kind: "insurance", sector: { ...sector, name: "Bảo hiểm", peers: 3 } })!;
  expect(insurer).toContain("trung vị của 3 doanh nghiệp cùng ngành Bảo hiểm (ICB cấp 2, HOSE)");
  expect(insurer).toContain("gồm cả bảo hiểm nhân thọ (BVH) và phi nhân thọ");
  const builder = sectorNote({ kind: "general", sector: { ...sector, name: "Xây dựng công trình", peers: 29, level: 4 } })!;
  expect(builder).toContain("trung vị của 29 doanh nghiệp cùng ngành Xây dựng công trình (ICB cấp 4, HOSE)");  // cấp 4 (28/11/2026)
  expect(sectorNote({ kind: "general", sector: { ...sector, name: "Viễn thông", level: 2 } })).toContain("(ICB cấp 2, HOSE)");
  expect(sectorNote({ kind: "general", sector: { ...sector, name: "Công nghiệp tổng hợp", level: 3 } })).toContain("Công nghiệp tổng hợp (ICB cấp 3, HOSE)");
  expect(sectorNote({ kind: "bank", sector: null })).toBeNull();
});

it("turns the sector's quarterly medians into the table's periods", async () => {
  const { sectorHistory } = await import("./financial-tables");
  const ratios = { kind: "bank" as const, quarters: [{ date: "2026-06-30", label: "Q2/2026" }, { date: "2026-09-30", label: "Q3/2026" }], metrics: [],
    sector: { name: "Ngân hàng", quarter: "2026-09-30", peers: 21, medians: {}, counts: {}, history: { BAD_LOANS_RATIO_AQ: [null, "0.0222"] } } };
  expect(sectorHistory(ratios)).toEqual({ BAD_LOANS_RATIO_AQ: { "2026-Q2": null, "2026-Q3": "0.0222" } });
  expect(sectorHistory({ ...ratios, sector: null })).toEqual({});
});
