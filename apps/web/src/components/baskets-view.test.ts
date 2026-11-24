import { describe, expect, it } from "vitest";
import { basketHeld, basketPyramid, basketResult, type BasketRow } from "./baskets-view";

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

describe("pyramid shapes per basket", () => {
  const shapes = { counts: { upright: 2, inverted: 1, mixed: 0 }, compared: 3, uncompared: 1, mean_above_share: null, enough: false };
  it("counts each shape, what could not be compared, and the mean share above the first buy only from five periods", () => {
    expect(basketPyramid({ ...row, pyramid: shapes })).toBe("2 xuôi · 1 ngược · 0 xen kẽ · 1 chưa so được · chưa đủ 5 đợt");
    expect(basketPyramid({ ...row, pyramid: { ...shapes, counts: { upright: 3, inverted: 1, mixed: 1 }, compared: 5, uncompared: 0, enough: true,
      mean_above_share: "0.4250" } })).toBe("3 xuôi · 1 ngược · 1 xen kẽ · bình quân 42,5% tiền bỏ vào ở giá cao hơn lần mua đầu");
  });
  it("says when a basket has no period with a second buy, and shows nothing when not computed", () => {
    expect(basketPyramid({ ...row, pyramid: { ...shapes, counts: { upright: 0, inverted: 0, mixed: 0 }, compared: 0, uncompared: 0 } })).toBe("chưa có đợt mua thêm");
    expect(basketPyramid({ ...row, pyramid: null })).toBe("—");
  });
});
