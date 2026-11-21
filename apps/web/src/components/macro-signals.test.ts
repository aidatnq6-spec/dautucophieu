import { describe, expect, it } from "vitest";
import { type Signal, signalNext, signalSince, signalSummary, signalThresholds, signalValue } from "./macro-signals";

const light = (id: Signal["id"], value: string | null, yellow: string, red: string, more: Partial<Signal> = {}): Signal =>
  ({ id, name: id, level: "green", value, latest_date: "2026-11-20", yellow, red, down_yellow: null, down_red: null, since: null, max_age_days: 7,
     spark: [], next: null, level_since: null, level_since_open: false, link: "wti", ...more });

describe("Đèn tín hiệu rủi ro vĩ mô", () => {
  it("says each light's value in its own words", () => {
    expect(signalValue(light("oil", "-0.2113", "0.10", "0.20"))).toBe("−21,1% trong 30 ngày");
    expect(signalValue(light("fx_gap", "0.0184", "0.01", "0.02"))).toBe("tự do cao hơn 1,84%");
    expect(signalValue(light("foreign", "3", "5", "10"))).toBe("bán ròng 3 phiên liên tiếp");
    expect(signalValue(light("interbank", "3.1", "5", "7"))).toBe("3,10%/năm");
    expect(signalValue(light("usd", null, "0.02", "0.04"))).toBe("");
  });
  it("gives the yellow and red thresholds the owner approved", () => {
    expect(signalThresholds(light("oil", null, "0.10", "0.20"))).toBe("vàng ≥ +10% · đỏ ≥ +20%");
    expect(signalThresholds(light("usd", null, "0.02", "0.04"))).toBe("vàng ≥ +2% · đỏ ≥ +4%");
    expect(signalThresholds(light("foreign", null, "5", "10"))).toBe("vàng ≥ 5 phiên · đỏ ≥ 10 phiên");
    expect(signalThresholds(light("interbank", null, "5", "7"))).toBe("vàng ≥ 5%/năm · đỏ ≥ 7%/năm");
  });
  it("adds oil's falling side to its thresholds", () => {
    expect(signalThresholds(light("oil", null, "0.10", "0.20", { down_yellow: "-0.15", down_red: "-0.25" })))
      .toBe("vàng ≥ +10% · đỏ ≥ +20% · giảm: vàng ≤ −15% · đỏ ≤ −25%");
  });
  it("says how far the next level is, in the light's own unit", () => {
    expect(signalNext(light("fx_gap", "0.0119", "0.01", "0.02", { level: "yellow", next: { level: "red", by: "0.0081" } }))).toBe("còn 0,81 điểm % nữa là đỏ");
    expect(signalNext(light("foreign", "4", "5", "10", { next: { level: "yellow", by: "1" } }))).toBe("thêm 1 phiên bán ròng là vàng");
    expect(signalNext(light("interbank", "4.68", "5", "7", { next: { level: "yellow", by: "0.32" } }))).toBe("còn 0,32 điểm % nữa là vàng");
    expect(signalNext(light("oil", "0.3", "0.10", "0.20", { level: "red" }))).toBe("đang ở mức đỏ");
  });
  it("says since when a light holds its level, and sums the lights up", () => {
    expect(signalSince(light("oil", "-0.17", "0.10", "0.20", { level: "yellow", level_since: "2026-11-16" }))).toBe("Vàng từ 16/11");
    expect(signalSince(light("usd", "0", "0.02", "0.04", { level_since: "2026-10-22", level_since_open: true }))).toBe("Xanh ít nhất từ 22/10");
    const rows = [light("oil", "1", "1", "2", { level: "yellow" }), light("usd", "0", "1", "2"), light("fx_gap", null, "1", "2", { level: "missing" })];
    expect(signalSummary(rows)).toBe("0 đỏ · 1 vàng · 1 xanh · 1 chưa có số");
  });
});
