import { describe, expect, it } from "vitest";
import { yearsLine } from "./property-projects";

describe("yearsLine", () => {
  it("lists the owner's yearly figures in tỷ đồng", () => {
    expect(yearsLine({ "2026": "1500", "2027": "4900.5" })).toBe("2026: 1.500 · 2027: 4.900,5");
    expect(yearsLine({})).toBe("—");
  });
});
