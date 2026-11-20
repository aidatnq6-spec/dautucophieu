import { describe, expect, it } from "vitest";
import { priceNote } from "./gold-price-note";

const up = { basis: "kind" as const, from: "2026-10-01", to: "2026-11-01", days: 31, change: "0.1230", strong: true };

describe("the note where gold is recorded", () => {
  it("names the price, the move and its dates, and points to the pyramid's share", () => {
    expect(priceNote(up, "Nhẫn tròn Phú Quý 999.9")).toBe("Giá Nhẫn tròn Phú Quý 999.9 (giá mua vào Phú Quý) đã tăng 12,3% trong 31 ngày "
      + "(01/10/2026 → 01/11/2026). Mua bán vàng theo tỷ trọng của Tháp tài sản (10–15%), không theo giá.");
  });
  it("says when the world price stands in, and a fall reads as a fall", () => {
    expect(priceNote({ ...up, basis: "world", change: "-0.1250" }, "Vàng miếng SJC")).toBe("Giá vàng thế giới (PAXG-USD; giá Vàng miếng SJC chưa đủ 30 ngày) "
      + "đã giảm 12,5% trong 31 ngày (01/10/2026 → 01/11/2026). Mua bán vàng theo tỷ trọng của Tháp tài sản (10–15%), không theo giá.");
    expect(priceNote({ ...up, basis: "world" }, null)).toContain("Giá vàng thế giới (PAXG-USD) đã tăng");
  });
  it("is silent below the threshold or without a move", () => {
    expect(priceNote({ ...up, strong: false }, "x")).toBeNull();
    expect(priceNote(null, "x")).toBeNull();
  });
});
