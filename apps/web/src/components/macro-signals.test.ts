import { describe, expect, it } from "vitest";
import { type Signal, signalAge, signalMove, signalNext, signalSince, signalSummary, signalThresholds, signalValue } from "./macro-signals";

const light = (id: Signal["id"], value: string | null, yellow: string, red: string, more: Partial<Signal> = {}): Signal =>
  ({ id, name: id, level: "green", value, latest_date: "2026-11-20", yellow, red, down_yellow: null, down_red: null, since: null, max_age_days: 7,
     spark: [], next: null, level_since: null, level_since_open: false, link: "#chi-so-wti", move: null, ...more });

describe("Đèn tín hiệu rủi ro vĩ mô", () => {
  it("says each light's value in its own words", () => {
    expect(signalValue(light("oil", "-0.2113", "0.10", "0.20"))).toBe("−21,1% trong 30 ngày");
    expect(signalValue(light("fx_gap", "0.0184", "0.01", "0.02"))).toBe("tự do cao hơn 1,84%");
    expect(signalValue(light("foreign", "3", "5", "10"))).toBe("bán ròng 3 phiên liên tiếp");
    expect(signalValue(light("interbank", "3.1", "5", "7"))).toBe("3,10%/năm");
    expect(signalValue(light("usd", null, "0.02", "0.04"))).toBe("");
  });
  it("gives the yellow and red thresholds the owner approved", () => {
    expect(signalThresholds(light("oil", null, "0.10", "0.20"))).toBe("cảnh báo ≥ +10% · nguy hiểm ≥ +20%");
    expect(signalThresholds(light("usd", null, "0.02", "0.04"))).toBe("cảnh báo ≥ +2% · nguy hiểm ≥ +4%");
    expect(signalThresholds(light("foreign", null, "5", "10"))).toBe("cảnh báo ≥ 5 phiên · nguy hiểm ≥ 10 phiên");
    expect(signalThresholds(light("interbank", null, "5", "7"))).toBe("cảnh báo ≥ 5%/năm · nguy hiểm ≥ 7%/năm");
  });
  it("adds oil's falling side to its thresholds", () => {
    expect(signalThresholds(light("oil", null, "0.10", "0.20", { down_yellow: "-0.15", down_red: "-0.25" })))
      .toBe("cảnh báo ≥ +10% · nguy hiểm ≥ +20% · giảm: cảnh báo ≤ −15% · nguy hiểm ≤ −25%");
  });
  it("says how far the next level is, in the light's own unit", () => {
    expect(signalNext(light("fx_gap", "0.0119", "0.01", "0.02", { level: "yellow", next: { level: "red", by: "0.0081" } }))).toBe("còn 0,81 điểm % nữa là mức nguy hiểm");
    expect(signalNext(light("foreign", "4", "5", "10", { next: { level: "yellow", by: "1" } }))).toBe("thêm 1 phiên bán ròng là mức cảnh báo");
    expect(signalNext(light("interbank", "4.68", "5", "7", { next: { level: "yellow", by: "0.32" } }))).toBe("còn 0,32 điểm % nữa là mức cảnh báo");
    expect(signalNext(light("oil", "0.3", "0.10", "0.20", { level: "red" }))).toBe("đang ở mức nguy hiểm");
  });
  it("says since when a light holds its level, and sums the lights up", () => {
    expect(signalSince(light("oil", "-0.17", "0.10", "0.20", { level: "yellow", level_since: "2026-11-16" }))).toBe("Cảnh báo từ 16/11");
    expect(signalSince(light("usd", "0", "0.02", "0.04", { level_since: "2026-10-22", level_since_open: true }))).toBe("Bình thường ít nhất từ 22/10");
    const rows = [light("oil", "1", "1", "2", { level: "yellow" }), light("usd", "0", "1", "2"), light("fx_gap", null, "1", "2", { level: "missing" })];
    expect(signalSummary(rows)).toBe("0 nguy hiểm · 1 cảnh báo · 1 bình thường · 1 chưa có số");
  });
  it("says which way each light moved, with its own colour", () => {
    expect(signalMove(light("oil", "-0.173", "0.10", "0.20", { move: { direction: "down", bad: false, by: "0.173" } })))
      .toEqual({ text: "▼ giảm · chiều tốt", tone: "good" });
    expect(signalMove(light("fx_gap", "0.0119", "0.01", "0.02", { move: { direction: "up", bad: true, by: "0.0069" } })))
      .toEqual({ text: "▲ tăng 0,69 điểm % so với 30 ngày trước · chiều xấu", tone: "bad" });
    expect(signalMove(light("interbank", "4.68", "5", "7", { move: { direction: "flat", bad: null, by: "0.02" } })))
      .toEqual({ text: "→ đi ngang so với 30 ngày trước", tone: "flat" });
    expect(signalMove(light("foreign", "4", "5", "10", { move: { direction: "up", bad: true, by: "4" } })))
      .toEqual({ text: "▲ đang bán ròng · chiều xấu", tone: "bad" });
  });
  it("reads the four lights added on 21/11/2026 in their own units", () => {
    expect(signalValue(light("fx_ceiling", "0.037", "0.02", "0.01"))).toBe("còn 3,70% tới trần biên độ");
    expect(signalThresholds(light("fx_ceiling", null, "0.02", "0.01"))).toBe("cảnh báo ≤ 2% · nguy hiểm ≤ 1% tới trần");
    expect(signalValue(light("us10y", "-0.21", "0.3", "0.5"))).toBe("−0,21 điểm % trong 30 ngày");
    expect(signalThresholds(light("us10y", null, "0.3", "0.5"))).toBe("cảnh báo ≥ +0,3 · nguy hiểm ≥ +0,5 điểm %");
    expect(signalValue(light("pe", "0.025", "0.80", "0.90", { pe: "10.65" }))).toBe("P/E 10,65 · cao hơn hoặc bằng 2,5% số phiên 5 năm");
    expect(signalValue(light("pmi", "52.3", "50", "48"))).toBe("PMI 52,3");
    expect(signalThresholds(light("pmi", null, "50", "48"))).toBe("cảnh báo < 50 · nguy hiểm < 48");
    expect(signalNext(light("pmi", "52.3", "50", "48", { next: { level: "yellow", by: "2.3" } }))).toBe("còn 2,3 điểm nữa là mức cảnh báo");
    expect(signalMove(light("fx_ceiling", "0.037", "0.02", "0.01", { move: { direction: "down", bad: true, by: "0.0019" } })))
      .toEqual({ text: "▼ giảm 0,19 điểm % so với 30 ngày trước · chiều xấu", tone: "bad" });
    expect(signalMove(light("pmi", "52.3", "50", "48", { move: { direction: "up", bad: false, by: "0.4" } })))
      .toEqual({ text: "▲ tăng 0,4 điểm so với tháng trước · chiều tốt", tone: "good" });
  });

  it("says a market light is old by HOSE sessions and the others by days", () => {
    expect(signalAge(light("interbank", "4.5", "5", "7", { level: "stale", max_age_sessions: 5 }))).toBe("quá 5 phiên HOSE chưa có số mới");
    expect(signalAge(light("oil", "0.1", "0.10", "0.20", { level: "stale", max_age_days: 10 }))).toBe("quá 10 ngày");
  });
});
