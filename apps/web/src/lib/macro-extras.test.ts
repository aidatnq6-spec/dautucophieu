import { describe, expect, it } from "vitest";
import { parseFx, parseRate, spreadPath, swapCost } from "./macro-extras";

describe("swapCost", () => {
  it("annualises the forward premium over the tenor and adds the USD rate for the cost of VND", () => {
    const c = swapCost({ spot: 24399, forward: 24704, months: 6, usdRate: 3.89 })!;
    expect(c.premium).toBeCloseTo(1.25, 2);
    expect(c.annual).toBeCloseTo(2.5, 2);
    expect(c.vnd).toBeCloseTo(6.39, 2);
  });
  it("gives nothing when an input is missing or not positive", () => {
    expect(swapCost({ spot: 0, forward: 24704, months: 6, usdRate: 3.89 })).toBeNull();
    expect(swapCost({ spot: 24399, forward: NaN, months: 6, usdRate: 3.89 })).toBeNull();
    expect(swapCost({ spot: 24399, forward: 24704, months: 0, usdRate: 3.89 })).toBeNull();
    expect(swapCost({ spot: 24399, forward: 24704, months: 6, usdRate: null })!.vnd).toBeNull();
  });
});

describe("inputs", () => {
  it("reads exchange rates with dots as thousands and rates with either decimal mark", () => {
    expect(parseFx("24.399")).toBe(24399);
    expect(parseFx("26 315,5")).toBe(26315.5);
    expect(parseFx("")).toBeNaN();
    expect(parseRate("3,89")).toBe(3.89);
    expect(parseRate("3.89")).toBe(3.89);
    expect(parseRate("")).toBeNull();
  });
});

describe("spreadPath", () => {
  it("places the points between the lowest and highest spread with zero inside the range", () => {
    const p = spreadPath([{ spread: "1" }, { spread: "-1" }, { spread: "0.5" }], 100, 40);
    expect(p.line).toBe("0,0 50,40 100,10");
    expect(p.zero).toBe(20);
  });
  it("keeps zero on the chart when every spread is positive", () => {
    expect(spreadPath([{ spread: "2" }, { spread: "1" }], 100, 40).zero).toBe(40);
  });
});
