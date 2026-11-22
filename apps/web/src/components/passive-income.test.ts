import { describe, expect, it } from "vitest";
import { neededText, realText, type Needed, type Real } from "./passive-income";

const real = (over: Partial<Real> = {}): Real => ({ required: "12500000000", real_rate: "8.00", months: 70, reached_on: "2032-09", reason: null,
  inflation: "4.5", inflation_from: null, margin: "0", ...over });

describe("Mốc tự do tài chính theo lợi suất thực", () => {
  it("says the inflation used, where it came from, the real return and when it is reached", () => {
    expect(realText(real(), "12,5")).toMatch(/^Lạm phát 4,5%\/năm \(bạn nhập\), lợi suất thực 8,00%\/năm: cần 12\.500\.000\.000.*khoảng 09\/2032/);
    expect(realText(real({ inflation_from: { source: "vn_cpi_yoy", date: "2026-10-31" }, margin: "44" }), "12,5"))
      .toMatch(/CPI Việt Nam so cùng kỳ tháng 10\/2026.*cộng biên an toàn 44%/);
  });
  it("says plainly when the return does not beat inflation", () => {
    expect(realText(real({ required: null, reason: "not_above_inflation", real_rate: "-0.50" }), "4")).toMatch(/không vượt lạm phát.*không có mốc/);
  });
});

describe("Lợi suất cần có", () => {
  const n = (over: Partial<Needed> = {}): Needed => ({ by_year: 2035, goal: "18000000000", goal_from: "real", status: "ok", rate: "14.20", deposit: "6",
    vnindex: { rate: "11.34", from: "2000-07-28", to: "2026-11-20" }, own: { rate: null, reason: "short" },
    at_vnindex: { reached_on: "2037-06", contribution: "21000000" }, ...over });
  it("sets the rate needed beside real ones and says plainly when it is above VN-Index", () => {
    const lines = neededText(n());
    expect(lines[0]).toMatch(/cần lợi suất khoảng 14,20%\/năm\.$/);
    expect(lines[1]).toMatch(/tiết kiệm 12 tháng 6%; VN-Index bình quân 11,34%\/năm từ 2000.*sổ chưa đủ một năm/);
    expect(lines[2]).toMatch(/Cao hơn mức VN-Index.*06\/2037.*\/tháng để vẫn đạt đúng năm 2035/);
    expect(neededText(n({ rate: "9.00" }))).toHaveLength(2);
  });
  it("says when it is reached, not feasible or out of time", () => {
    expect(neededText(n({ status: "reached", rate: null }))[0]).toMatch(/đã đủ/);
    expect(neededText(n({ status: "not_feasible", rate: null }))[0]).toMatch(/không khả thi/);
    expect(neededText(n({ status: "no_time", rate: null }))[0]).toMatch(/đã hết/);
  });
});
