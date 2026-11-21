import { describe, expect, it } from "vitest";
import { stockNote } from "./equity-budget";

describe("stockNote", () => {
  it("names the price day and keeps the cost beside the market value", () => {
    const note = stockNote({ basis: "market", cost: "5000000", value: "6000000", unpriced: [], price_dates: ["2026-11-20"] });
    expect(note).toContain("theo thị giá 20/11");
    expect(note).toContain("giá vốn 5.000.000");
    expect(note).not.toContain("chưa có giá");
  });

  it("names a ticker without a recent close, which stays at cost", () => {
    const note = stockNote({ basis: "market", cost: "5000000", value: "5000000", unpriced: ["FPT"], price_dates: [] });
    expect(note).toContain("FPT chưa có giá gần đây, tính theo giá vốn");
  });
});
