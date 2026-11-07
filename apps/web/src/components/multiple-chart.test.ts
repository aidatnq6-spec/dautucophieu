import { expect, it } from "vitest";
import { periodText } from "./multiple-chart";

it("a point names the figures behind it: four quarters, a quarter's equity or a year", () => {
  expect(periodText("2026-Q3", "4 quý")).toBe("4 quý đến Q3/2026");
  expect(periodText("2026-Q3", "quý")).toBe("vốn chủ cuối Q3/2026");
  expect(periodText("2025", "năm")).toBe("số liệu năm 2025");
  expect(periodText("2025", undefined)).toBe("số liệu năm 2025");
});
