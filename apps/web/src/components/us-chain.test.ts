import { describe, expect, it } from "vitest";
import { chainSummary, fitLabel } from "./us-chain";

describe("chainSummary", () => {
  it("names the chain's way, then the links with it, against it, flat and missing", () => {
    expect(chainSummary({ mode: "tightening", driver: "us_cpi", nodes: [{ id: "us_cpi", direction: "up" }], with: ["us_rates", "dxy", "gold"],
      against: [], flat: ["usd_vnd"], missing: [] }))
      .toBe("CPI Mỹ tăng nên chuỗi đang theo chiều thắt chặt. Khớp chuỗi: lãi suất Mỹ, DXY, vàng. Đi ngang: tỷ giá USD/VND.");
    expect(chainSummary({ mode: "easing", driver: "us_rates", nodes: [{ id: "us_rates", direction: "down" }], with: ["dxy"], against: ["gold"],
      flat: [], missing: ["usd_vnd"] }))
      .toBe("Lãi suất Mỹ giảm nên chuỗi đang theo chiều nới lỏng. Khớp chuỗi: DXY. Ngược chuỗi: vàng. Chưa có số: tỷ giá USD/VND.");
    expect(chainSummary({ mode: null, driver: null, nodes: [], with: [], against: [], flat: [], missing: [] }))
      .toBe("Tuần này CPI Mỹ và lãi suất Mỹ đều đi ngang: chuỗi chưa có chiều rõ.");
  });
  it("labels each link by how it fits the chain", () => {
    expect(fitLabel("with", "tightening")).toEqual(["khớp chuỗi", "bad", "chain-pressure"]);
    expect(fitLabel("driver", "easing")).toEqual(["mở đầu chuỗi", "good", "chain-support"]);
    expect(fitLabel("against", "tightening")).toEqual(["ngược chuỗi", "warn", "chain-neutral"]);
  });
});
