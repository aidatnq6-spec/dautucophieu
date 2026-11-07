import { expect, it } from "vitest";
import { periodText, yearLabels } from "./multiple-chart";

it("a point names the figures behind it: four quarters, a quarter's equity or a year", () => {
  expect(periodText("2026-Q3", "4 quý")).toBe("4 quý đến Q3/2026");
  expect(periodText("2026-Q3", "quý")).toBe("vốn chủ cuối Q3/2026");
  expect(periodText("2025", "năm")).toBe("số liệu năm 2025");
  expect(periodText("2025", undefined)).toBe("số liệu năm 2025");
});

it("each year is labelled at its first month; a label crowded by the next one is dropped, and one at the left edge is kept", () => {
  const months = ["2017-12", "2018-01", "2018-02", "2018-03", "2018-04", "2018-05", "2019-01", "2019-02"];
  const x = (i: number) => 36 + i * 6;  // dense: 6 px a month, as the index charts from 12/2017
  expect(yearLabels(months, x, 36, 1)).toEqual([{ i: 1, year: "2018", anchor: "start" }, { i: 6, year: "2019", anchor: "middle" }]);
  expect(yearLabels(months, (i) => 36 + i * 100, 36, 1)).toEqual([{ i: 0, year: "2017", anchor: "start" }, { i: 1, year: "2018", anchor: "middle" },
    { i: 6, year: "2019", anchor: "middle" }]);
  expect(yearLabels(months, (i) => 36 + i * 100, 36, 2).map((l) => l.year)).toEqual(["2018"]);  // every other year on a phone
});
