import { describe, expect, it } from "vitest";
import { place } from "./watch-quadrant";

const p = { symbol: "AAA", pb: "1", cheaper_months: "0.25", months: 40, growth: "0.5", quarter: "2026-Q3", held: "400", zone: "cheap_growing" as const };

describe("place", () => {
  it("puts cheaper on the left, faster growth higher and a larger holding bigger", () => {
    expect(place(p, 800, 400, 1600)).toEqual({ x: 200, y: 100, r: 17, clipped: false });
    expect(place({ ...p, held: null }, 800, 400, 1600).r).toBe(5);
  });
  it("keeps a growth beyond 100% on the edge and marks it", () => {
    expect(place({ ...p, growth: "-3" }, 800, 400, 0)).toMatchObject({ y: 400, clipped: true });
  });
});
