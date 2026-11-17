import { describe, expect, it } from "vitest";
import { gapText } from "./building-tool";

describe("gapText", () => {
  it("says how far a yield sits above or below the deposit rate, in points", () => {
    expect(gapText(0.092, 0.06)).toBe("cao hơn 3,2 điểm %");
    expect(gapText(0.045, 0.06)).toBe("thấp hơn 1,5 điểm %");
  });
});
