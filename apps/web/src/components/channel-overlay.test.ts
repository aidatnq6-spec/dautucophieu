import { expect, it } from "vitest";
import { channelMarkers, channelSegments } from "./channel-overlay";
import type { Channels } from "./bar-channels";

const data: Channels = {
  symbol: "HPG", label: "HPG", unit: "nghìn đồng", basis: "ohlc", note: null, frame: "W", n: 5, reason: null, bars: 200, last_bar: "2026-11-02", in_progress: null,
  zero: 0, points: {},
  bases: [
    { cross: "2022-12-05", low_date: "2022-11-14", low: "7.98", zone_from: "2022-10-31", zone_to: "2022-12-05", vs_prev: null },
    { cross: "2023-11-13", low_date: "2023-10-23", low: "15.28", zone_from: "2023-10-09", zone_to: "2023-11-13", vs_prev: "higher" },
  ],
  channels: [
    { kind: "basic", from: { date: "2022-11-14", price: "7.98" }, to: { date: "2025-04-07", price: "15.85" }, slope: "0.06",
      top: { date: "2023-09-11", price: "19.88" }, lower_now: "20.95", upper_now: "30.02", double_now: "39.09" },
    { kind: "final", from: { date: "2025-04-07", price: "15.85" }, to: { date: "2026-03-23", price: "22.54" }, slope: "0.13",
      top: { date: "2025-12-01", price: "28" }, lower_now: "26.69", upper_now: "35.30", double_now: "43.91" },
  ],
  status: null,
  breaks: [{ date: "2026-06-01", close: "23.75", lower: "23.88", from: { date: "2025-04-07", price: "15.85" }, to: { date: "2026-03-23", price: "22.54" } }],
};

it("each channel runs from its first joining point to the last finished bar, the upper line the channel's width above", () => {
  const segs = channelSegments(data);
  const basicLower = segs.find((s) => s.key === "basic-lower")!;
  expect(basicLower.points).toEqual([{ t: "2022-11-14", p: 7.98 }, { t: "2026-11-02", p: 20.95 }]);
  const finalUpper = segs.find((s) => s.key === "final-upper")!;
  expect(finalUpper.points[0].t).toBe("2025-04-07");
  expect(finalUpper.points[0].p).toBeCloseTo(15.85 + (35.3 - 26.69), 6);
  expect(finalUpper.points[1]).toEqual({ t: "2026-11-02", p: 35.3 });
  expect(segs.find((s) => s.key === "final-double")!.points[1]).toEqual({ t: "2026-11-02", p: 43.91 });
  expect(segs.some((s) => s.key === "basic-double")).toBe(false);  // the doubled width is drawn for the final channel only
  expect(segs.find((s) => s.key === "final-lower")!.width).toBeGreaterThan(segs.find((s) => s.key === "basic-lower")!.width);
});

it("each base zone is a level at its low from the zone's start to its bullish cross", () => {
  expect(channelSegments(data).filter((s) => s.key.startsWith("zone")).map((s) => s.points)).toEqual([
    [{ t: "2022-10-31", p: 7.98 }, { t: "2022-12-05", p: 7.98 }],
    [{ t: "2023-10-09", p: 15.28 }, { t: "2023-11-13", p: 15.28 }],
  ]);
});

it("markers name the zones, point 0 and each break, in time order", () => {
  expect(channelMarkers(data).map((m) => [m.time, m.text, m.position])).toEqual([
    ["2022-11-14", "d1 · 0", "belowBar"],
    ["2023-10-23", "d2", "belowBar"],
    ["2026-06-01", "phá kênh", "aboveBar"],
  ]);
});

it("nothing is drawn without channels or a finished bar", () => {
  expect(channelSegments({ ...data, channels: [], bases: [] })).toEqual([]);
  expect(channelSegments({ ...data, last_bar: null })).toEqual([]);
});
