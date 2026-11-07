import { expect, it } from "vitest";
import { planCard, planLine } from "./annual-plans";

const B = 1e9;
const plan = {
  year: "2026", origin: "owner" as const, source: "Nghị quyết ĐHCĐ 2026", profit_kind: "npat", profit_label: "LNST", plan_revenue: "210000", plan_profit: "22000", through: "2026-Q3",
  revenue: { actual: String(170274 * B), plan: String(210000 * B), ratio: "0.8108", reason: null },
  profit: { actual: String(23746 * B), plan: String(22000 * B), ratio: "1.0794", reason: null },
};

it("a card reads as the screenshot: year-to-date against the plan, in percent and tỷ đồng", () => {
  expect(planCard(plan, "revenue")).toEqual({ title: "DT lũy kế Q3/2026 · % kế hoạch", value: "81,1%", note: "170.274 / KH 210.000 tỷ" });
  expect(planCard(plan, "profit")).toEqual({ title: "LNST lũy kế Q3/2026 · % kế hoạch", value: "107,9%", note: "23.746 / KH 22.000 tỷ" });
});

it("a line without a plan has no card and a line without quarters says why", () => {
  expect(planCard({ ...plan, revenue: null }, "revenue")).toBeNull();
  const none = { ...plan, through: null, profit: { actual: null, plan: String(22000 * B), ratio: null, reason: "Chưa có số quý 1/2026" } };
  expect(planCard(none, "profit")).toEqual({ title: "LNST 2026 · % kế hoạch", value: "—", note: "Chưa có số quý 1/2026 · KH 22.000 tỷ" });
});

it("the list line names the plan, where it came from, and marks CafeF's", () => {
  expect(planLine(plan)).toBe("2026: doanh thu 210.000 tỷ, LNST 22.000 tỷ · nguồn: Nghị quyết ĐHCĐ 2026");
  expect(planLine({ ...plan, origin: "cafef", source: "CafeF (Kế hoạch kinh doanh), đọc 07/11/2026", plan_revenue: null }))
    .toBe("2026: LNST 22.000 tỷ · theo CafeF (Kế hoạch kinh doanh), đọc 07/11/2026 — nhập số của bạn để thay");
});
