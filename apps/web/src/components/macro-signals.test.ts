import { describe, expect, it } from "vitest";
import { type Signal, signalThresholds, signalValue } from "./macro-signals";

const light = (id: Signal["id"], value: string | null, yellow: string, red: string): Signal =>
  ({ id, name: id, level: "green", value, latest_date: "2026-11-20", yellow, red, since: null, max_age_days: 7, spark: [] });

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
});
