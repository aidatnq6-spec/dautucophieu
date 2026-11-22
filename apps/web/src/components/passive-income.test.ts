import { describe, expect, it } from "vitest";
import { realText, type Real } from "./passive-income";

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
