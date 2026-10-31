import { expect, it } from "vitest";
import { levelInput } from "./price-alerts";

it("reads levels the Vietnamese way: comma for decimals, dots for thousands", () => {
  expect(levelInput("56,3")).toBe("56.3");
  expect(levelInput("1.800")).toBe("1800");
  expect(levelInput(" 1.741,62 ")).toBe("1741.62");
  expect(levelInput("20")).toBe("20");
  expect(levelInput("abc")).toBeNull();
  expect(levelInput("0")).toBeNull();
  expect(levelInput("-5")).toBeNull();
});
