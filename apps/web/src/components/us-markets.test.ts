import { describe, expect, it } from "vitest";
import { usPct } from "./us-markets";

describe("Chứng khoán Mỹ", () => {
  it("writes a change with two decimals and a sign, or a dash with nothing to compare", () => {
    expect(usPct("0.0164")).toBe("+1,64%");
    expect(usPct("-0.037")).toBe("−3,70%");
    expect(usPct(null)).toBe("—");
  });
});
