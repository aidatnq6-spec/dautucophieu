import { expect, it } from "vitest";
import { periodStart } from "./trend-board";

it("keys a day's price to its week's Monday or its month's first day, like the weekly and monthly candles", () => {
  expect(periodStart("2026-10-30", "1W")).toBe("2026-10-26");  // a Friday
  expect(periodStart("2026-10-26", "1W")).toBe("2026-10-26");  // the Monday itself
  expect(periodStart("2026-11-01", "1W")).toBe("2026-10-26");  // a Sunday belongs to the week before
  expect(periodStart("2026-10-30", "1M")).toBe("2026-10-01");
  expect(periodStart("2026-10-30", "1D")).toBe("2026-10-30");
});
