import { expect, it } from "vitest";
import { type Drawing, clickStep, drawingsFor, roundPrice, when } from "./chart-drawings";

const hline: Drawing = { id: "a", symbol: "FPT", kind: "hline", interval: null, price: "56.3", points: null, created_at: "" };
const daily: Drawing = { id: "b", symbol: "FPT", kind: "trend", interval: "1D", price: null, created_at: "",
  points: [{ t: "2026-09-01", p: "50" }, { t: "2026-10-30", p: "55" }] };
const other: Drawing = { ...hline, id: "c", symbol: "HPG" };

it("shows a level on both frames and a trend line on the frame it was drawn on", () => {
  expect(drawingsFor([hline, daily, other], "FPT", "1D").map((d) => d.id)).toEqual(["a", "b"]);
  expect(drawingsFor([hline, daily, other], "FPT", "1H").map((d) => d.id)).toEqual(["a"]);
});

it("rounds the cursor's price to two decimals as a plain positive decimal", () => {
  expect(roundPrice(56.2849)).toBe("56.28");
  expect(roundPrice(1741.6)).toBe("1741.6");
  expect(roundPrice(70000)).toBe("70000");
  expect(roundPrice(0.001)).toBeNull();
  expect(roundPrice(-3)).toBeNull();
  expect(roundPrice(Number.NaN)).toBeNull();
});

it("a level takes one click, a trend line two on different candles", () => {
  expect(clickStep("pointer", null, { t: "2026-10-30", p: 55 })).toEqual({ pending: null, add: null });
  expect(clickStep("hline", null, { t: "2026-10-30", p: 55.123 })).toEqual({ pending: null, add: { kind: "hline", price: "55.12" } });
  const first = clickStep("trend", null, { t: "2026-09-01", p: 50 });
  expect(first).toEqual({ pending: { t: "2026-09-01", p: "50" }, add: null });
  expect(clickStep("trend", first.pending, { t: "2026-09-01", p: 52 })).toEqual({ pending: { t: "2026-09-01", p: "50" }, add: null });
  expect(clickStep("trend", first.pending, { t: "2026-10-30", p: 55.5 })).toEqual({
    pending: null, add: { kind: "trend", points: [{ t: "2026-09-01", p: "50" }, { t: "2026-10-30", p: "55.5" }] } });
  expect(clickStep("hline", null, { t: "2026-10-30", p: -1 })).toEqual({ pending: null, add: null });
});

it("names a point's candle by day, and by day and hour on the hourly frame", () => {
  expect(when("2026-10-01")).toBe("01/10/2026");
  expect(when(Date.UTC(2026, 9, 30, 9) / 1000)).toBe("30/10 09:00");  // 09:00 in Hà Nội, stored as wall-clock seconds
});
