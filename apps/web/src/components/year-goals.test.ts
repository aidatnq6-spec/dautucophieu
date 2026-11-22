import { describe, expect, it } from "vitest";
import { rateInput, rowText } from "./year-goals";

describe("Mục tiêu năm", () => {
  it("reads the savings rate as a percentage", () => {
    expect(rateInput("30")).toBe("0.3");
    expect(rateInput("30,5")).toBe("0.305");
    expect(rateInput("")).toBe("");
    expect(rateInput("100")).toBeNull();
    expect(rateInput("abc")).toBeNull();
  });

  it("says where a goal stands and what it lacks, never a forecast", () => {
    const row = { id: "contribution" as const, goal: "120000000", now: "30000000", share: "0.25", pace: "0.5014", behind: true };
    expect(rowText(row)).toMatch(/^đã góp 30\.000\.000.*: 25% mục tiêu, tiến độ đều 50%$/);
    expect(rowText({ ...row, id: "total_assets", share: null, start: null })).toBe("chưa có ảnh chụp cuối năm trước để tính quãng đường");
    expect(rowText({ ...row, id: "savings_rate", goal: "0.3", now: null, share: null, pace: null })).toBe("chưa có tháng Thu chi nào đã xong");
  });
});
