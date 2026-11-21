import { describe, expect, it } from "vitest";
import { changePct, enough, evidence, figureText } from "./history-stats";

describe("figureText", () => {
  it("names the month for a World Bank figure and the day for a daily one", () => {
    const c = (kind: "monthly" | "daily", figure_date: string | null) => ({ id: "x", label: "x", kind, state: true, known_on: null, figure_date, from: null });
    expect(figureText(c("monthly", "2026-07-31"))).toBe("số tháng 07/2026");
    expect(figureText(c("daily", "2026-11-19"))).toBe("số ngày 19/11/2026");
    expect(figureText(c("daily", null))).toBe("chưa có số");
  });
});

const s = (n: number, ind: number, t: string | null) => ({ n, n_independent: ind, mean: "0.1", median: "0.1", win_rate: "0.6", t });

describe("Thống kê lịch sử", () => {
  it("writes a change with one decimal and a sign", () => {
    expect(changePct("0.2058")).toBe("+20,6%");
    expect(changePct("-0.057")).toBe("−5,7%");
    expect(changePct(null)).toBe("—");
  });

  it("says plainly how much a group's figures rest on", () => {
    expect(evidence(s(588, 6, "1.58"))).toBe("6 khoảng độc lập, chưa rõ khác 0");
    expect(evidence(s(66, 1, null))).toBe("chỉ 1 khoảng độc lập: rất ít");
    expect(evidence(s(900, 40, "2.4"))).toBe("40 khoảng độc lập, t = 2,4");
    expect(evidence(s(0, 0, null))).toBe("chưa có mẫu");
  });

  it("hides a group's figures below 5 independent windows", () => {
    expect(enough({ ...s(66, 4, null), enough: false })).toBe(false);
    expect(enough({ ...s(900, 40, "2.4"), enough: true })).toBe(true);
    expect(enough(s(66, 4, null))).toBe(false);  // an older answer without the flag
  });
});
