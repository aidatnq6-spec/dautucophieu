import { describe, expect, it } from "vitest";
import { draftOf, offList, ruleLabel, rulesFrom } from "./basket-rules";

describe("basket reminder levels", () => {
  it("says where a ticker's level comes from, as the reminder does", () => {
    expect(ruleLabel({ source: "basket", basket: "Ngắn hạn", threshold: "0.07" })).toBe("giỏ Ngắn hạn: 7%");
    expect(ruleLabel({ source: "default", basket: null, threshold: "0.30" })).toBe("mức chung: 30%");
    expect(ruleLabel({ source: "off", basket: "Dài hạn", threshold: null })).toBe("giỏ Dài hạn: không nhắc");
    expect(ruleLabel({ source: "default", basket: null, min_gain: null, share: null })).toBe("mức chung: chưa đặt");
    expect(ruleLabel({ source: "basket", basket: "Bắt đáy", min_gain: "0.2", share: "0.5" })).toBe("giỏ Bắt đáy: lãi từ 20%, trả lại từ 50%");
    expect(ruleLabel({ source: "basket", basket: "A", threshold: "0.075" })).toBe("giỏ A: 7,5%");
  });

  it("reads a saved basket into the fields and back, an older basket at the common level", () => {
    const draft = draftOf({ id: "b1", name: "A" });
    expect(draft).toEqual({ drawdown: "default", threshold: "", giveback: "default", minGain: "", share: "" });
    expect(rulesFrom(draft)).toEqual({ drawdown: { mode: "default" }, giveback: { mode: "default" } });
    const own = draftOf({ id: "b1", name: "A", drawdown: { mode: "custom", threshold: "0.07" }, giveback: { mode: "custom", min_gain: "0.2", share: "0.5" } });
    expect(own).toEqual({ drawdown: "custom", threshold: "7", giveback: "custom", minGain: "20", share: "50" });
    expect(rulesFrom({ ...own, threshold: "7,5" })).toEqual({ drawdown: { mode: "custom", threshold: "0.075" },
      giveback: { mode: "custom", min_gain: "0.2", share: "0.5" } });
    expect(rulesFrom({ ...own, drawdown: "off", giveback: "off" })).toEqual({ drawdown: { mode: "off" }, giveback: { mode: "off" } });
  });

  it("refuses a level that is missing or outside the common limits", () => {
    const own = { drawdown: "custom", threshold: "7", giveback: "custom", minGain: "20", share: "50" } as const;
    expect(rulesFrom({ ...own, threshold: "" })).toBe("Sụt giảm: nhập ngưỡng riêng từ 1% đến 95%.");
    expect(rulesFrom({ ...own, threshold: "96" })).toBe("Sụt giảm: nhập ngưỡng riêng từ 1% đến 95%.");
    expect(rulesFrom({ ...own, share: "" })).toBe("Lãi đã trả lại: nhập cả hai ngưỡng riêng (lãi từ 1% đến 1000%, trả lại từ 1% đến 100%).");
    expect(rulesFrom({ ...own, minGain: "1001" })).toBe("Lãi đã trả lại: nhập cả hai ngưỡng riêng (lãi từ 1% đến 1000%, trả lại từ 1% đến 100%).");
  });

  it("names the holdings whose basket does not remind", () => {
    expect(offList([{ symbol: "KDH", rule: { source: "off", basket: "Dài hạn", threshold: null } },
      { symbol: "FPT", rule: { source: "default", basket: null, threshold: "0.3" } }, { symbol: "VNINDEX" }])).toBe("KDH (giỏ Dài hạn)");
  });
});
