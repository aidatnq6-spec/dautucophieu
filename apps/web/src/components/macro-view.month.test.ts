import { describe, expect, it } from "vitest";
import { lastMonth } from "./macro-view";

describe("lastMonth", () => {
  it("is the month before today's, across a year end", () => {
    expect(lastMonth("2026-11-16")).toBe("2026-10");
    expect(lastMonth("2027-01-03")).toBe("2026-12");
  });
});
