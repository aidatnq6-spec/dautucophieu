import { describe, expect, it } from "vitest";
import { bandAxis } from "./valuation-bands";

const band = (low: string, high: string) => ({ id: "x", name: "x", low, mid: null, high, source: "", auto: true });

describe("bandAxis", () => {
  it("spans every bar and the close on round steps", () => {
    expect(bandAxis([band("32828", "73515"), band("44000", "65100")], "44400")).toEqual({ lo: 30000, hi: 80000, ticks: [30000, 40000, 50000, 60000, 70000, 80000] });
    expect(bandAxis([band("20000", "30000")], null).ticks[0]).toBe(15000);  // 5,000 steps under 50,000
  });
});
