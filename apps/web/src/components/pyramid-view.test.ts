import { describe, expect, it } from "vitest";
import { largestText, pyramidSummary, type PyramidRow } from "./pyramid-view";

const row: PyramidRow = { key: "FPT@2026-02-02", symbol: "FPT", start: "2026-02-02", end: null, label: "inverted", reason: null,
  buys: [{ on: "2026-02-02", outlay: "5000000", level: "0.0000" }, { on: "2026-02-20", outlay: "18000000", level: "0.2000" }],
  above_share: "0.7826", largest: { on: "2026-02-20", outlay: "18000000", level: "0.2000" }, mean_above: "18000000", mean_below: "5000000" };

describe("pyramid", () => {
  it("says where the largest buy came against the first", () => {
    expect(largestText(row)).toBe("18.000.000 đ ngày 20/02/2026, giá cao hơn lần mua đầu 20,0%");
    expect(largestText({ ...row, largest: { on: "2026-02-02", outlay: "5000000", level: "0.0000" } })).toBe("5.000.000 đ ngày 02/02/2026, lần mua đầu");
    expect(largestText({ ...row, largest: { on: "2026-03-01", outlay: "9000000", level: "-0.1500" } })).toBe("9.000.000 đ ngày 01/03/2026, giá thấp hơn lần mua đầu 15,0%");
    expect(largestText({ ...row, largest: null })).toBe("—");
  });
  it("counts the shapes and gives the mean only from five periods", () => {
    expect(pyramidSummary({ counts: { upright: 1, inverted: 2, mixed: 0 }, compared: 3, mean_above_share: null, enough: false }))
      .toBe("3 đợt so được: 1 tháp xuôi, 2 tháp ngược, 0 xen kẽ. Chưa đủ 5 đợt để tính bình quân.");
    expect(pyramidSummary({ counts: { upright: 2, inverted: 3, mixed: 1 }, compared: 6, mean_above_share: "0.6123", enough: true }))
      .toBe("6 đợt so được: 2 tháp xuôi, 3 tháp ngược, 1 xen kẽ. Bình quân 61,2% tiền của một đợt bỏ vào ở giá cao hơn lần mua đầu.");
    expect(pyramidSummary({ counts: { upright: 0, inverted: 0, mixed: 0 }, compared: 0, mean_above_share: null, enough: false }))
      .toBe("Chưa có đợt nào so được.");
  });
});
