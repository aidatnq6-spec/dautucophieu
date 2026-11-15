import { describe, expect, it } from "vitest";
import { advancesText, borrowingText, carryText, sectorText, type Carry } from "./balance-watch";

const C: Carry = { quarter: "2026-Q3", kind: "carry", missing: [], fin_income: "28000000000", interest: "8000000000", net: "20000000000",
  avg_cash_like: "400000000000", avg_debt: "200000000000", yield: "0.0700", cost: "0.0400", spread: "0.0300" };

describe("carryText", () => {
  it("sets the yield on cash against the cost of borrowing and names borrowing cheap to deposit dear", () => {
    expect(carryText(C)).toBe("Bốn quý đến Q3/2026: doanh thu tài chính 28 tỷ trên tiền và đầu tư ngắn hạn bình quân 400 tỷ (khoảng 7,0%/năm); "
      + "lãi vay 8 tỷ trên nợ vay bình quân 200 tỷ (khoảng 4,0%/năm). Chênh lệch +3,0 điểm %. Doanh nghiệp vừa vay vừa giữ nhiều tiền và thu từ tiền "
      + "nhiều hơn trả lãi vay: kiểu \"vay rẻ, gửi đắt\".");
  });
  it("says when it costs more than it earns, when there is no borrowing, and what is missing", () => {
    expect(carryText({ ...C, kind: null, spread: "-0.1300" })).toContain("Chênh lệch −13,0 điểm %. Thu từ tiền thấp hơn chi phí vay.");
    expect(carryText({ ...C, kind: "no_debt", cost: null, spread: null })).toBe(
      "Bốn quý đến Q3/2026: không vay; doanh thu tài chính 28 tỷ trên tiền và đầu tư ngắn hạn bình quân 400 tỷ (khoảng 7,0%/năm).");
    expect(carryText({ ...C, missing: ["2025-Q3", "2026-Q1"] })).toBe("Chưa đủ bốn quý liên tiếp đến Q3/2026 để tính: thiếu số của Q3/2025, Q1/2026.");
    expect(carryText({ ...C, quarter: null })).toContain("chưa có doanh thu tài chính");
  });
});

describe("borrowingText", () => {
  it("names how many times borrowing grew in two years when it is flagged", () => {
    expect(borrowingText({ kind: "fast_borrowing", quarter: "2026-Q3", debt: "450000000000", debt_2y_ago: "200000000000", ratio: "2.2500" }))
      .toBe("Nợ vay Q3/2026 là 450 tỷ, gấp 2,25 lần hai năm trước (200 tỷ). Vay tăng nhanh làm tăng chi phí lãi và rủi ro khi lãi suất lên: đọc thuyết minh xem vay cho dự án nào.");
  });
  it("says when borrowing started from nothing, and is silent otherwise", () => {
    expect(borrowingText({ kind: "fast_borrowing", quarter: "2026-Q3", debt: "50000000000", debt_2y_ago: "0", ratio: null })).toContain("hai năm trước không vay");
    expect(borrowingText({ kind: null, quarter: "2026-Q3", debt: "1", debt_2y_ago: "1", ratio: "1.0000" })).toBeNull();
  });
});

describe("advancesText", () => {
  const base = { quarter: "2026-Q3", advances_yoy: "-0.4167", profit_yoy: "11.5000" };
  it("reads handing over homes already paid for", () => {
    expect(advancesText({ ...base, kind: "handover" })).toContain("lợi nhuận tăng 1.150% so cùng kỳ trong khi tiền khách trả trước giảm 42%");
  });
  it("reads money collected ahead of handover", () => {
    expect(advancesText({ ...base, kind: "collecting", advances_yoy: "0.5000" })).toContain("tăng 50% so cùng kỳ");
  });
  it("gives the change with the thresholds when there is no clear reading, and says when the figure is missing", () => {
    expect(advancesText({ ...base, kind: null, advances_yoy: "0.0500" })).toContain("tăng 5% so cùng kỳ: chưa rõ chiều nào");
    expect(advancesText({ ...base, kind: null, advances_yoy: null })).toContain("Chưa đủ số");
  });
});

describe("sectorText", () => {
  it("adds up the sector and compares two years on the tickers that have both ends", () => {
    expect(sectorText("Bất động sản", { members: 7, growth_2y: "0.3500", compared: 6, top: "VHM",
      quarters: [{ quarter: "2026-Q3", count: 7, debt: "1200000000000000", net_debt: "900000000000000", net_count: 7 }] }))
      .toBe("Ngành Bất động sản (7 mã theo dõi, 7 mã có số Q3/2026): tổng nợ vay 1.200.000 tỷ, nợ vay ròng 900.000 tỷ. So với hai năm trước: tăng 35% trên 6 mã có đủ số, tăng nhiều nhất là VHM.");
  });
});
