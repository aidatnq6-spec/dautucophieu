import { describe, expect, it } from "vitest";
import { linePaths } from "./held-charts";

describe("linePaths", () => {
  it("puts both lines on one scale so the gap between them is real", () => {
    const p = linePaths([{ date: "a", value: "100", index: "100" }, { date: "b", value: "120", index: "110" }], 100, 40);
    expect(p).toEqual({ stock: "M0.0,40.0 L100.0,0.0", index: "M0.0,40.0 L100.0,20.0", lo: 100, hi: 120 });
  });
});
