import { describe, expect, it } from "vitest";
import { basketHeld, basketResult, type BasketRow } from "./baskets-view";

const row: BasketRow = { id: "b1", name: "Ngắn hạn", closed: 1, open: 1, realised: "1098500", released: "6001500", realised_ratio: "0.1830",
  win_rate: null, mean_days: null, enough: false, open_cost: "1000500", unrealised: "249500", missing: [] };

describe("baskets", () => {
  it("states the realised gain and, from five closed periods, the share with a gain and the days held", () => {
    expect(basketResult(row)).toBe("Lãi đã chốt 1.098.500 đ (+18,3% trên giá vốn đã bán) · chưa đủ 5 đợt đã đóng");
    expect(basketResult({ ...row, enough: true, win_rate: "0.6000", mean_days: "4.0", closed: 5 }))
      .toBe("Lãi đã chốt 1.098.500 đ (+18,3% trên giá vốn đã bán) · 60,0% đợt có lãi · nắm bình quân 4,0 ngày");
    expect(basketResult({ ...row, realised: "0", released: "0", realised_ratio: null })).toBe("Chưa bán lần nào · chưa đủ 5 đợt đã đóng");
  });
  it("values what is still held, or names the tickers without a price", () => {
    expect(basketHeld(row)).toBe("Giá vốn 1.000.500 đ, lãi chưa chốt 249.500 đ");
    expect(basketHeld({ ...row, unrealised: null, missing: ["VCB"] })).toBe("Giá vốn 1.000.500 đ; chưa có giá: VCB");
    expect(basketHeld({ ...row, open: 0, unrealised: null })).toBe("—");
  });
});
