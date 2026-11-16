import { describe, expect, it } from "vitest";
import { linePath, yRange } from "./sjc-gap";

describe("the SJC gap chart", () => {
  it("spans the values and the threshold with some room", () => {
    expect(yRange([12, 14], 15)).toEqual([11, 16]);
    expect(yRange([13], null)).toEqual([12, 14]);
  });
  it("draws one point per day from left to right, higher values nearer the top", () => {
    expect(linePath([10, 20], [10, 20], 100, 50)).toBe("M0,50 L100,0");
    expect(linePath([15], [10, 20], 100, 50)).toBe("M50,25");
  });
});
