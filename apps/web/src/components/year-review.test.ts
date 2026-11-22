import { describe, expect, it } from "vitest";
import { missingText, pctText } from "./year-review";

describe("Tổng kết năm", () => {
  it("writes shares with one decimal, signed or not", () => {
    expect(pctText("0.045")).toBe("+4,5%");
    expect(pctText("-0.1234")).toBe("−12,3%");
    expect(pctText("0.3", false)).toBe("30,0%");
    expect(pctText(null)).toBe("—");
  });
  it("names the months not entered and never fills them", () => {
    expect(missingText(["2026-02", "2026-05"])).toBe("chưa nhập 2 tháng: 02/2026, 05/2026");
    expect(missingText([])).toBeNull();
  });
});
