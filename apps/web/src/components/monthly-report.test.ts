import { describe, expect, it } from "vitest";
import { monthSentence } from "./monthly-report";

describe("monthSentence", () => {
  it("puts the month's return beside VN-Index's", () => {
    expect(monthSentence([{ month: "2026-10", portfolio: "0.032", vnindex: "-0.011" }], "2026-10"))
      .toBe("Danh mục +3,2%, VN-Index −1,1% trong tháng: hơn thị trường 4,3%.");
    expect(monthSentence([], "2026-10")).toBeNull();
  });
});
