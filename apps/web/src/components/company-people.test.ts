import { describe, expect, it } from "vitest";
import { isOld } from "./company-people";

describe("isOld", () => {
  it("marks a disclosure more than 12 months before the day it was read", () => {
    expect(isOld("2023-07-05", "2026-11-14T02:00:00+00:00")).toBe(true);
    expect(isOld("2025-11-14", "2026-11-14T02:00:00+00:00")).toBe(false);  // exactly 12 months: not yet
    expect(isOld("2025-11-13", "2026-11-14T02:00:00+00:00")).toBe(true);
    expect(isOld(null, "2026-11-14T02:00:00+00:00")).toBe(false);  // no date: nothing to say
    expect(isOld("2023-07-05", null)).toBe(false);
  });
});
