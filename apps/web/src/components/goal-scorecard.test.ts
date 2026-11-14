import { describe, expect, it } from "vitest";
import { scorecardRows } from "./goal-scorecard";

describe("scorecardRows", () => {
  it("lists every goal set, and says where to set the missing ones", () => {
    const rows = scorecardRows({
      passive: { goal: { target: "10000000" }, result: { required: "2000000000", income_now: "4000000", progress: "0.4", reached_on: null } },
      contrib: null,
      budget: { budget: { pyramid: { layers: [{ id: "reserve", share: null, target_min: null, target_max: null, status: "fixed" },
        { id: "stocks", share: "0.42", target_min: "0.2", target_max: "0.35", status: "over" }] } } },
      book: { liquidity: { now: "50000000", reserve: "100000000", status: "short" } },
      theses: { theses: [{ symbol: "FPT", progress: { return: "20", months: 12, due: "2027-11-14", gain: "0.1", reached: false, overdue: false } },
        { symbol: "HPG", progress: null }] } });
    expect(rows.map((r) => [r.goal, r.status, r.done])).toEqual([
      ["Dòng tiền thụ động mỗi tháng", "behind", 0.4], ["Góp vốn đều", "unset", null], ["Tỷ trọng Cổ phiếu", "over", null],
      ["Quỹ dự phòng (tiền rút được ngay)", "behind", 0.5], ["Luận điểm FPT: +20% trong 12 tháng", "behind", 0.5]]);
    expect(rows[2].target).toBe("20%–35%");
  });
});
