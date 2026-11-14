import { describe, expect, it } from "vitest";
import { gapText } from "./thesis-questions";

describe("gapText", () => {
  it("counts the open gaps over all of them", () => {
    const q = (done: boolean[]) => ({ status: null, summary: "", points: [], gaps: done.map((d, i) => ({ id: String(i), text: "x", ref: "", done: d })) });
    expect(gapText({ business: q([false, true]), valuation: q([false]) })).toBe("2/3 việc mở");
    expect(gapText({})).toBe("chưa ghi chỗ trống");
    expect(gapText({ business: q([true]) }, { strategy: ["Chưa có kế hoạch"] })).toBe("1/2 việc mở (1 tự động)");
  });
});
