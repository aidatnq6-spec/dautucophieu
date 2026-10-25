import { expect, it } from "vitest";
import { formatRatio, formatVnd, parseMoneyInput } from "./format";

it.each([["500000000", "500.000.000 đ"], ["2500000.5", "2.500.001 đ"], ["-300000", "−300.000 đ"], ["0", "0 đ"], [null, "—"],
  ["123456789012345678901234", "123.456.789.012.345.678.901.234 đ"]])("formats %s", (v, out) => {
  expect(formatVnd(v)).toBe(out);
});
it.each([["0.125", "12,5%"], ["1", "100,0%"], ["0.6", "60,0%"]])("ratio %s", (v, out) => expect(formatRatio(v)).toBe(out));
it.each([["500.000.000", "500000000"], ["1 000", "1000"], ["12,5", "12.5"], ["-1", null], ["abc", null], ["", null]])("parses %s", (v, out) => {
  expect(parseMoneyInput(v)).toBe(out);
});

import { percentToRatio } from "./format";
it.each([["0,15", "0.0015"], ["1", "0.01"], ["12,5", "0.125"], ["100", "1"], ["101", null], ["x", null], ["0", "0"]])("percent %s", (v, out) => {
  expect(percentToRatio(v)).toBe(out);
});

import { hanoiDate } from "./format";
it.each([["-0.02", "−2,0%"], ["-0.125", "−12,5%"], ["-0", "0,0%"]])("negative ratio %s", (v, out) => expect(formatRatio(v)).toBe(out));
it("uses the Hanoi calendar date", () => {
  expect(hanoiDate(new Date("2027-01-14T23:30:00Z"))).toBe("2027-01-15");
  expect(hanoiDate(new Date("2027-01-15T16:59:00Z"))).toBe("2027-01-15");
});
