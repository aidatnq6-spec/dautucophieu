import { describe, expect, it } from "vitest";
import { type Card, moveCard } from "./idea-board";

const card = (id: string, stage: Card["stage"]): Card => ({ id, symbol: id.toUpperCase() + "AA", stage, note: "", lesson: "", moved_on: "2026-11-01", days: 0, hints: [] });

describe("moveCard", () => {
  it("moves one card a column and leaves the others", () => {
    const out = moveCard([card("a", "idea"), card("b", "holding")], "b", 1)!;
    expect(out.map((c) => c.stage)).toEqual(["idea", "sold"]);
  });
  it("stops at either end", () => {
    expect(moveCard([card("a", "idea")], "a", -1)).toBeNull();
    expect(moveCard([card("a", "sold")], "a", 1)).toBeNull();
  });
});
