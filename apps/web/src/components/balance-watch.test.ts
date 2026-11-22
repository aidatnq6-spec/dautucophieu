import { describe, expect, it } from "vitest";
import { advancesText, borrowingText, coverageText, inventoryPaceText, inventoryText, lendingText, provisionFlowText, carryText, dsoText, otherSectorText, prepayDaysText, provisionText, raiseText, revisionText, sectorText, type Carry } from "./balance-watch";

describe("otherSectorText", () => {
  it("sets the ticker's other receivables and loans against the sector, and says when it stands out", () => {
    expect(otherSectorText({ quarter: "2026-Q3", share: "0.2700", sector_median: "0.0600", sector_count: 3, high: true }))
      .toBe("Phải thu khác và cho vay Q3/2026 bằng 27,0% tổng tài sản; trung vị ngành 6,0% (3 mã theo dõi khác). Cao hơn hẳn các mã cùng ngành: "
        + "không phải đặc thù ngành, nên đọc thuyết minh xem phải thu của ai.");
    expect(otherSectorText({ quarter: "2026-Q3", share: "0.1900", sector_median: null, sector_count: 0, high: null })).toContain("chưa có mã cùng ngành");
  });
});

describe("prepayment readings", () => {
  it("sets the days of prepayment against a year before and the sector", () => {
    expect(prepayDaysText({ quarter: "2026-Q3", days: "477", year_ago: "160", change: "317", sector_median: "236", sector_count: 5 }))
      .toBe("Số ngày ứng trước nhà cung cấp Q3/2026: 477 ngày, dài hơn 317 ngày so với cùng kỳ năm trước (160 ngày); trung vị ngành 236 ngày (5 mã theo dõi khác).");
  });
  it("names a raise whose money went out as prepayments, and one that did not", () => {
    const e = { issue_date: "2025-08-20", quarter: "2025-Q3", capital_added: "50000000000", prepay_before: "10000000000", prepay_after: "40000000000",
      after_quarter: "2025-Q4", prepay_added: "30000000000", flag: true };
    expect(raiseText(e)).toContain("Đợt huy động vốn ngày 20/08/2025 thêm 50 tỷ vốn điều lệ (Q3/2025); ngay sau đó trả trước người bán từ 10 tỷ (trước đợt) lên 40 tỷ (Q4/2025), tăng 30 tỷ");
    expect(raiseText({ ...e, prepay_after: "11000000000", prepay_added: "1000000000", flag: false })).toContain("thấp hơn một nửa số vốn vừa góp");
  });
});

describe("dsoText", () => {
  it("sets the days to collect against a year before and the sector", () => {
    expect(dsoText({ quarter: "2026-Q3", days: "70", year_ago: "55", change: "15", sector_median: "48", sector_count: 3 }))
      .toBe("Số ngày thu tiền Q3/2026: 70 ngày, chậm hơn 15 ngày so với cùng kỳ năm trước (55 ngày); trung vị ngành 48 ngày (3 mã theo dõi khác).");
    expect(dsoText({ quarter: "2026-Q3", days: "40", year_ago: null, change: null, sector_median: null, sector_count: 0 })).toBe("Số ngày thu tiền Q3/2026: 40 ngày.");
    expect(dsoText({ quarter: "2026-Q3", days: null, year_ago: null, change: null, sector_median: null, sector_count: 0 })).toContain("Chưa đủ");
  });
});

describe("provisionText", () => {
  it("names the provision, its share, and a jump", () => {
    expect(provisionText({ quarter: "2026-Q3", amount: "20000000000", share: "0.1333", year_ago: "10000000000", kind: "jump" }))
      .toBe("Q3/2026: dự phòng phải thu ngắn hạn khó đòi 20 tỷ, bằng 13,3% phải thu ngắn hạn trước dự phòng. Tăng mạnh so với cùng kỳ năm trước (10 tỷ): "
        + "doanh nghiệp vừa thừa nhận thêm khoản khó thu; đọc thuyết minh xem của khách hàng nào.");
    expect(provisionText({ quarter: "2026-Q3", amount: "0", share: "0.0000", year_ago: "0", kind: "none" })).toBe("Q3/2026: không trích dự phòng phải thu ngắn hạn khó đòi.");
    expect(provisionText({ quarter: null, amount: null, share: null, year_ago: null, kind: null })).toContain("chưa có dòng dự phòng");
  });
});

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
    expect(carryText({ ...C, kind: "unusual_income", yield: "0.2340" })).toContain("không coi là lãi gửi");
    expect(carryText({ ...C, kind: "low_interest", cost: "0.0027" })).toContain("vốn hóa vào dự án");
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

describe("revisionText", () => {
  it("says the period, the line, the old and new figure and the day seen", () => {
    expect(revisionText({ kind: "years", period: "2024", line: "npat_parent", label: "LNST công ty mẹ", old: "100000000000", new: "80000000000", seen_on: "2026-11-22" }))
      .toMatch(/^Năm 2024, LNST công ty mẹ: 100.* → 80.* \(thấy 22\/11\/2026\)$/);
    expect(revisionText({ kind: "quarters", period: "2025-Q2", line: "pbt", label: "LNTT", old: "1", new: "2", seen_on: "2026-12-01" })).toMatch(/^Quý 2\/2025, LNTT:/);
  });
});

describe("lendingText", () => {
  it("sets lending against equity, says why it is flagged, and never fills a blank", () => {
    expect(lendingText({ quarter: "2026-Q1", share: "0.35", year_ago: "0.1", flag: "high" })).toMatch(/35.*vốn chủ; cùng kỳ năm trước 10.*Từ 30% vốn chủ/);
    expect(lendingText({ quarter: "2026-Q1", share: "0.21", year_ago: "0.1", flag: "rising" })).toMatch(/Tăng từ 10 điểm/);
    expect(lendingText({ quarter: "2026-Q1", share: null, year_ago: null, flag: null })).toMatch(/^Chưa tính được/);
  });
});

describe("provisionFlowText", () => {
  const row = (change: string | null, pbt: string | null, share: string | null) => ({ quarter: "2026-Q1", balance: "1", change, pbt, share, release: false });
  it("says the quarter's change against its profit, and that a fall cannot be told apart", () => {
    expect(provisionFlowText({ rows: [row("19000000000", "160000000000", "0.1188")], flag: false, quarter: "2026-Q1" })).toMatch(/tăng .* bằng 11,9% LNTT của quý\.$/);
    const fall = provisionFlowText({ rows: [row("-40000000000", "200000000000", "0.2")], flag: true, quarter: "2026-Q1" });
    expect(fall).toMatch(/giảm .* bằng 20,0% LNTT.*hoàn nhập.*xóa nợ/);
    expect(provisionFlowText({ rows: [row("-4000000000", "-5000000000", null)], flag: false, quarter: "2026-Q1" })).toMatch(/không dương/);
    expect(provisionFlowText({ rows: [row(null, null, null)], flag: false, quarter: "2026-Q1" })).toMatch(/^Chưa tính được/);
  });
});

describe("coverageText", () => {
  const r = (quarter: string, coverage: string | null) => ({ quarter, customers: null, prepay: null, loans: null, other: null, provision: null, total: "487000000000",
    gross: "553000000000", coverage, total_share: null, other_share: null, dso: null, prepay_days: null });
  it("sets the latest coverage against a year before and the first of the twelve quarters", () => {
    const rows = [r("2023-Q1", "0.05"), r("2024-Q4", "0.085"), r("2025-Q4", "0.1193")];
    expect(coverageText(rows)).toMatch(/^Q4\/2025: dự phòng bằng 11,9% phải thu trước dự phòng .*; cùng kỳ năm trước 8,5%; Q1\/2023 5,0%\.$/);
    expect(coverageText([r("2025-Q4", null)])).toMatch(/^Chưa tính được/);
  });
});

describe("inventoryText", () => {
  const row = (quarter: string, net: string | null, share: string | null, gross: string | null = null, provision: string | null = null, coverage: string | null = null) =>
    ({ quarter, gross, provision, net, coverage, share });
  it("says the latest net, its share of assets and the provision, against a year before", () => {
    const text = inventoryText({ rows: [row("2020-Q4", "19422000000000", "0.4222"), row("2021-Q4", "29167000000000", "0.4632", "29850000000000", "683000000000", "0.0229")] });
    expect(text).toMatch(/^Q4\/2021: tồn kho thuần .* bằng 46,3% tổng tài sản; dự phòng giảm giá .* bằng 2,3% giá gốc .*Cùng kỳ năm trước: .*\(42,2% tổng tài sản\)\.$/);
    expect(inventoryText({ rows: [row("2021-Q4", "1", null)] })).toMatch(/chưa có giá gốc và dự phòng/);
    expect(inventoryText({ rows: [] })).toBe("Báo cáo đã lưu chưa có dòng hàng tồn kho.");
  });
});

describe("inventoryPaceText", () => {
  const p = { quarter: "2025-Q4", days: "249", year_ago: "183", change: "66", sector_median: "91", sector_count: 3, inventory_growth: "0.5", cogs_growth: "0.1", flag: true };
  it("says the days against a year before and the sector, the growth, and why it is flagged", () => {
    expect(inventoryPaceText(p)).toMatch(/^Q4\/2025: tồn kho đủ 249 ngày giá vốn; cùng kỳ năm trước 183 ngày; trung vị ngành 91 ngày \(3 mã\)\. Tồn kho tăng 50,0% .* 10,0%\. Hàng nhập về/);
    expect(inventoryPaceText({ ...p, flag: false })).not.toMatch(/Hàng nhập về/);
    expect(inventoryPaceText({ ...p, days: null })).toMatch(/^Chưa tính được/);
  });
});
