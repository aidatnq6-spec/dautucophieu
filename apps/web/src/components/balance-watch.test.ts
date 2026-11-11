import { describe, expect, it } from "vitest";
import { advancesText, borrowingText, sectorText } from "./balance-watch";

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
