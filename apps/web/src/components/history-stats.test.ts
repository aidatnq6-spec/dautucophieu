import { describe, expect, it } from "vitest";
import { changePct, evidence } from "./history-stats";

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
});
