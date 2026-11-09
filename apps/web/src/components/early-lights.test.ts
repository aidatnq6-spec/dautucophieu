import { describe, expect, it } from "vitest";
import { bands } from "./early-lights";

describe("bands", () => {
  it("reads the thresholds in the direction they were written", () => {
    expect(bands("55", "75", "")).toEqual({ bad: "< 55", watch: "55–75", good: "≥ 75" });
    expect(bands("1.5", "0.9", "x")).toEqual({ bad: "> 1,5x", watch: "0,9–1,5x", good: "≤ 0,9x" });
  });
});
