import { describe, expect, it } from "vitest";
import { gapNote } from "./macro-view";

describe("gapNote", () => {
  it("names the month that has no change on a year and the blank month at the source", () => {
    expect(gapNote({ month: "2026-10", base: "2025-10" }))
      .toBe("Tháng 10/2026 chưa tính được so cùng kỳ vì nguồn để trống số tháng 10/2025; phần mềm không tự lấp.");
  });

  it("says nothing without a gap", () => {
    expect(gapNote(null)).toBeNull();
    expect(gapNote(undefined)).toBeNull();
  });
});
