import { describe, expect, it } from "vitest";
import { peNote } from "./financial-tables";

const base = { quarter: "2026-Q3", year_ago: "2025-Q3", ttm: "1", ttm_year_ago: "2" };

describe("peNote", () => {
  it("says a high P/E comes from fallen profit", () => {
    expect(peNote({ ...base, change: "-0.5000", kind: "earnings_drop" })).toBe("P/E đang cao vì lợi nhuận 4 quý đến Q3/2026 giảm 50% so với cùng kỳ, không phải vì giá đắt. Xem lợi nhuận có hồi phục không trước khi so P/E.");
  });
  it("warns a low P/E after a jump may not last", () => {
    expect(peNote({ ...base, change: "1.0000", kind: "earnings_spike" })).toContain("tăng 100% so với cùng kỳ");
  });
  it("says P/E means nothing on a loss", () => {
    expect(peNote({ ...base, change: null, kind: "loss" })).toContain("P/E không có ý nghĩa");
  });
  it("says nothing for an ordinary year or no data", () => {
    expect(peNote({ ...base, change: "0.1000", kind: null })).toBeNull();
    expect(peNote(null)).toBeNull();
  });
});
