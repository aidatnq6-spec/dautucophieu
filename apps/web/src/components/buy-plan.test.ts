import { describe, expect, it } from "vitest";
import { conditionValue, standing, type Tranche } from "./buy-plan";

const t: Tranche = { id: "a", symbol: "FPT", amount: "20000000", kind: "price_le", value: "90", note: "", status: "waiting", met_on: null, met_value: null,
  close: "100", close_date: "2026-11-13", distance: "-0.1", days_left: null };

describe("buy plan", () => {
  it("turns what is typed into the stored condition", () => {
    expect(conditionValue("price_le", "90,5")).toBe("90.5");
    expect(conditionValue("report", "Q4/2026")).toBe("2026-Q4");
    expect(conditionValue("date", "2026-12-01")).toBe("2026-12-01");
  });
  it("says how far a waiting tranche is and when a met one was met", () => {
    expect(standing(t)).toBe("đóng cửa 100,00 ngày 13/11/2026, cần giảm thêm 10,0%");
    expect(standing({ ...t, status: "met", met_on: "2026-11-20", met_value: "89.5" })).toBe("Đạt ngày 20/11/2026 (đóng cửa 89,50)");
    expect(standing({ ...t, kind: "date", value: "2026-12-01", days_left: 17 })).toBe("còn 17 ngày");
  });
});
