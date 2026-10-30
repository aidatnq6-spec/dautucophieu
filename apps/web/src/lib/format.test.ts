import { expect, it } from "vitest";
import { formatDecimal, formatRatio, formatVnd, parseMoneyInput } from "./format";

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

it("formatDecimal groups thousands and rounds half up on the string", () => {
  expect(formatDecimal("1774.15", 2)).toBe("1.774,15");
  expect(formatDecimal("1703.705", 2)).toBe("1.703,71");
  expect(formatDecimal("1700", 2)).toBe("1.700,00");
  expect(formatDecimal("-12.5", 1)).toBe("−12,5");
  expect(formatDecimal(null, 2)).toBe("—");
});

import { groupDigitsInput } from "./format";

it("groupDigitsInput groups whole đồng by thousands while typing and drops anything else", () => {
  expect(groupDigitsInput("1000000")).toBe("1.000.000");
  expect(groupDigitsInput("1800000000")).toBe("1.800.000.000");
  expect(groupDigitsInput("1.80000")).toBe("180.000");
  expect(groupDigitsInput("12a3 4")).toBe("1.234");
  expect(groupDigitsInput("007")).toBe("7");
  expect(groupDigitsInput("")).toBe("");
});

it("formatRatio with no decimals gives whole percents", () => {
  expect(formatRatio("0.35", 0)).toBe("35%");
  expect(formatRatio("0.05", 0)).toBe("5%");
  expect(formatRatio("0.9", 0)).toBe("90%");
  expect(formatRatio("-0.004", 0)).toBe("0%");
});
