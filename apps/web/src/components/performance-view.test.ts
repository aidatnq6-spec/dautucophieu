import { expect, it } from "vitest";
import { chartRows, skippedNote } from "./performance-view";

const series = [
  { date: "2027-01-05", portfolio: "100", vnindex: "100", value: "5000000" },
  { date: "2027-01-06", portfolio: "101.5", vnindex: "99.2", value: "5075000" },
  { date: "2027-01-07", portfolio: "103", vnindex: "100.4", value: "5150000" },
];

it("the data behind the chart keeps every session, newest first", () => {
  const rows = chartRows(series);
  expect(rows.map((r) => r.date)).toEqual(["2027-01-07", "2027-01-06", "2027-01-05"]);
  expect(rows[0]).toEqual({ date: "2027-01-07", portfolio: "103", vnindex: "100.4", value: "5150000" });
});

it("skipped sessions are named, not only counted", () => {
  expect(skippedNote([])).toBeNull();
  expect(skippedNote(["2027-01-08"])).toBe("Bỏ qua 1 phiên thiếu giá: 08/01/2027.");
  expect(skippedNote(["2027-01-08", "2027-01-11"])).toBe("Bỏ qua 2 phiên thiếu giá: 08/01/2027, 11/01/2027.");
});
