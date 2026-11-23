import { describe, expect, it } from "vitest";
import { accruedLine, fromInput, pageNote, provisionLine, quarterToEnter, sourceLine, type Accrued, type Provision } from "./bank-figures";

describe("accruedLine", () => {
  const base: Accrued = { quarter: "2026-Q3", ratio: "0.6364", ratio_year_ago: "0.5000", accrued_growth_yoy: "0.4000", income_growth_yoy: "0.1000", flag: true, why_not: null };
  it("states both growths behind the sign, the growths without it, and why it could not be weighed", () => {
    expect(accruedLine(base)).toBe("Lãi, phí phải thu tăng 40,0% so cùng kỳ, thu nhập lãi tăng 10,0%: phần lãi ghi nhận nhưng chưa thu bằng tiền tăng nhanh hơn.");
    expect(accruedLine({ ...base, flag: false })).toBe("Chưa thấy lãi dự thu tăng nhanh hơn thu nhập lãi (lãi dự thu tăng 40,0%, thu nhập lãi tăng 10,0% so cùng kỳ).");
    expect(accruedLine({ ...base, flag: null, why_not: "Chưa có lãi dự thu và thu nhập lãi của 2025-Q3 để so cùng kỳ." }))
      .toBe("Chưa có lãi dự thu và thu nhập lãi của 2025-Q3 để so cùng kỳ.");
  });
  it("writes a fall as a fall (review 23/11/2026)", () => {
    expect(accruedLine({ ...base, accrued_growth_yoy: "0.0500", income_growth_yoy: "-0.2000" }))
      .toBe("Lãi, phí phải thu tăng 5,0% so cùng kỳ, thu nhập lãi giảm 20,0%: phần lãi ghi nhận nhưng chưa thu bằng tiền tăng nhanh hơn.");
  });
});

describe("provisionLine", () => {
  const base: Provision = { rows: [], quarter: "2026-Q3", share: "0.1333", credit_cost: null, credit_cost_missing: [], expense_growth_yoy: "-0.4000",
    bad_growth_qoq: "0.0800", bad_now: "27", bad_prev: "25", flag: true, why_not: null };
  it("states the amounts when there was no bad debt the quarter before", () => {
    expect(provisionLine({ ...base, bad_growth_qoq: null, bad_now: "5", bad_prev: "0" }))
      .toBe("Chi phí dự phòng giảm 40,0% so cùng kỳ trong khi nợ nhóm 3–5 tăng từ 0 lên 5 tỷ so quý trước: lợi nhuận được đỡ bởi giảm trích lập.");
  });
  it("states the cut and the bad debt behind the sign, says when there is none, and why it could not be weighed", () => {
    expect(provisionLine(base)).toBe("Chi phí dự phòng giảm 40,0% so cùng kỳ trong khi nợ nhóm 3–5 tăng 8,0% so quý trước: lợi nhuận được đỡ bởi giảm trích lập.");
    expect(provisionLine({ ...base, flag: false })).toMatch(/^Chưa thấy lợi nhuận được đỡ/);
    expect(provisionLine({ ...base, flag: null, why_not: "Chưa có nợ nhóm 3–5 của 2026-Q3 và quý trước để xét." })).toBe("Chưa có nợ nhóm 3–5 của 2026-Q3 và quý trước để xét.");
  });
});

describe("sourceLine", () => {
  it("names where each figure of the quarter came from, groups 1–5 as one", () => {
    const vietcap = { group1: "Vietcap", group2: "Vietcap", group3: "Vietcap", group4: "Vietcap", group5: "Vietcap" } as const;
    expect(sourceLine({ ...vietcap, reserve: "VNDirect", accrued_interest: "VNDirect" }))
      .toBe("Nợ nhóm 1–5: Vietcap · dự phòng rủi ro cho vay, lãi và phí phải thu: VNDirect");
    expect(sourceLine({ ...vietcap, group2: "số nhập tay", reserve: "số nhập tay", real_estate_loans: "số nhập tay" }))
      .toBe("Nợ nhóm 1, 3, 4, 5: Vietcap · nợ nhóm 2, dự phòng rủi ro cho vay, dư nợ bất động sản: số nhập tay");
    expect(sourceLine({})).toBe("");
  });
});

describe("fromInput", () => {
  it("reads Vietnamese, thousands-only and decimal-point numbers without scaling them", () => {
    expect(fromInput("537.304,578")).toBe("537304.578");
    expect(fromInput("537304,578")).toBe("537304.578");
    expect(fromInput("447.734")).toBe("447734");
    expect(fromInput("537304.578")).toBe("537304.578");
    expect(fromInput("11,5")).toBe("11.5");
    expect(fromInput(" 7 808 ")).toBe("7808");
  });
});

describe("pageNote", () => {
  it("names the page and file a value came from, and says when it was read from a scanned image", () => {
    expect(pageNote(31, "mbb.pdf", false)).toBe("trang 31 trong mbb.pdf");
    expect(pageNote(31, "mbb.pdf", true)).toBe("trang 31 trong mbb.pdf · đọc từ ảnh (OCR), so lại từng chữ số");
  });
});

describe("quarterToEnter", () => {
  it("suggests the last quarter that has ended, or the one before it once that is saved", () => {
    expect(quarterToEnter(new Date(2026, 10, 10), [])).toBe("2026-Q3");
    expect(quarterToEnter(new Date(2026, 10, 10), ["2026-Q3"])).toBe("2026-Q2");
    expect(quarterToEnter(new Date(2026, 10, 10), ["2026-Q3", "2026-Q2"])).toBe("2026-Q1");
    expect(quarterToEnter(new Date(2027, 1, 3), [])).toBe("2026-Q4");
    expect(quarterToEnter(new Date(2026, 3, 1), ["2026-Q1", "2025-Q4", "2025-Q3", "2025-Q2", "2025-Q1", "2024-Q4", "2024-Q3", "2024-Q2"])).toBe("2026-Q1");
  });
});
