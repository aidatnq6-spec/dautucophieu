import { describe, expect, it } from "vitest";
import { axisLines, bottlenecks, radarAxes } from "./health-radar";

describe("radarAxes", () => {
  it("measures each factor against what is needed and leaves out what has no figures", () => {
    const axes = radarAxes({ wealth: { check: { rate: "0.2", target: "0.4" } }, conc: { limit: "0.2", tickers: [{ symbol: "A", weight: "0.4" }, { symbol: "B", weight: "0.1" }] },
      passive: null, contrib: null, budget: { budget: { pyramid: { layers: [{ id: "reserve", status: "fixed", target_min: null }, { id: "stocks", status: "over", target_min: "0.2" },
        { id: "gold", status: "ok", target_min: "0" }] } } }, book: { liquidity: { now: "150", reserve: "100" } }, theses: { missing: ["B"] } });
    expect(axes.map((a) => [a.id, a.value])).toEqual([["savings", 0.5], ["reserve", 1], ["spread", 0.5], ["pyramid", 0.5], ["passive", null], ["contrib", null], ["theses", 0.5]]);
    expect(bottlenecks(axes).map((a) => a.id)).toEqual(["savings", "spread"]);
  });
});

describe("axisLines", () => {
  it("splits a long axis name at the space nearest its middle", () => {
    expect(axisLines("Luận điểm cho mã đang nắm")).toEqual(["Luận điểm cho", "mã đang nắm"]);
    expect(axisLines("Tháp tài sản")).toEqual(["Tháp tài sản"]);
  });
});
