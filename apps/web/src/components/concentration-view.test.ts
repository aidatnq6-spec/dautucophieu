import { expect, it } from "vitest";
import { sectorsAddInformation } from "./concentration-view";

it("the sector table is worth showing only when some sector holds more than one ticker", () => {
  expect(sectorsAddInformation([{ symbols: ["KDH"] }, { symbols: ["SSI"] }])).toBe(false);
  expect(sectorsAddInformation([{ symbols: ["MBB", "VCB"] }, { symbols: ["SSI"] }])).toBe(true);
  expect(sectorsAddInformation([])).toBe(false);
});
