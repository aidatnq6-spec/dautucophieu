import { describe, expect, it } from "vitest";
import { floorScale, growthScale, labelSpots, place } from "./watch-quadrant";

const p = { symbol: "AAA", pb: "1", cheaper_months: "0.25", months: 40, growth: "0.5", quarter: "2026-Q3", held: "400", zone: "cheap_growing" as const };

describe("place", () => {
  it("puts cheaper on the left, faster growth higher on a compressed scale and a larger holding bigger", () => {
    const b = place(p, 800, 400, 1600);
    expect(b.x).toBe(200);
    expect(b.y).toBeCloseTo(200 - growthScale(0.5) * 200, 6);
    expect(b.r).toBe(12);
    expect(place({ ...p, held: null }, 800, 400, 1600).r).toBe(4);
  });
  it("keeps a growth beyond 300% on the edge and marks it", () => {
    expect(place({ ...p, growth: "-5" }, 800, 400, 0)).toMatchObject({ y: 400, clipped: true });
    expect(growthScale(3)).toBe(1);
    expect(growthScale(1)).toBeGreaterThan(0.45);  // ±100% sits about halfway, not at the edge
  });
});

describe("labelSpots", () => {
  it("moves a name that would overlap another, and gives up only when no side is free", () => {
    const spots = labelSpots([{ key: "A", x: 100, y: 100, r: 4, text: "AAA", first: true }, { key: "B", x: 104, y: 100, r: 4, text: "BBB", first: false }], 400, 300);
    expect(spots.A).toEqual({ x: 100, y: 93, anchor: "middle" });
    expect(spots.B).not.toBeNull();
    expect(spots.B!.y).not.toBe(93);
  });
});

describe("floorScale", () => {
  it("stops the plot just below the lowest ticker instead of at −300%", () => {
    expect(floorScale([0.2, -0.95])).toBeCloseTo(growthScale(-1), 9);
    expect(floorScale([0.2, 0.1])).toBeCloseTo(growthScale(-0.5), 9);
    expect(floorScale([-7])).toBeCloseTo(-1, 9);
  });
});
