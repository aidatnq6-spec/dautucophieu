import { describe, expect, it } from "vitest";
import { barSpans, bridgeBars, bridgeNotes, changeTone, fit, mergeSmall, squarify } from "./asset-views";

describe("squarify", () => {
  it("fills the box exactly, each area in proportion to its value", () => {
    const rects = squarify([6, 6, 4, 3, 2, 2, 1], 6, 4);
    const area = rects.reduce((a, r) => a + r.w * r.h, 0);
    expect(area).toBeCloseTo(24, 6);
    expect(rects[0].w * rects[0].h).toBeCloseTo(6, 6);
    expect(rects[6].w * rects[6].h).toBeCloseTo(1, 6);
    for (const r of rects) { expect(r.x).toBeGreaterThanOrEqual(-1e-9); expect(r.x + r.w).toBeLessThanOrEqual(6 + 1e-9); expect(r.y + r.h).toBeLessThanOrEqual(4 + 1e-9); }
  });
  it("gives nothing a size when there is nothing to draw", () => {
    expect(squarify([0, 0], 10, 10)).toEqual([{ x: 0, y: 0, w: 0, h: 0 }, { x: 0, y: 0, w: 0, h: 0 }]);
  });
});

describe("changeTone", () => {
  it("colours by gain on cost and greys an asset without a market price", () => {
    expect(changeTone("0.25")).toBe("am-g3");
    expect(changeTone("-0.03")).toBe("am-r1");
    expect(changeTone(null)).toBe("am-none");
  });
});

describe("bridge", () => {
  const b = { status: "ok" as const, month: "2026-10", start_day: "2026-09-30", end_day: "2026-10-31", start: "100", end: "130", other: "0",
    steps: [{ id: "flows", amount: "20" }, ...Array.from({ length: 10 }, (_, i) => ({ id: `ticker:T${i}`, symbol: `T${i}`, amount: String(10 - i) })),
      { id: "dividends", amount: "5" }, { id: "costs", amount: "-50" }] };
  it("draws the eight largest tickers and puts the rest together, between the start and the end", () => {
    const bars = bridgeBars(b);
    expect(bars.map((x) => x.label)).toEqual(["Đầu tháng", "Tiền nộp/rút", "T0", "T1", "T2", "T3", "T4", "T5", "T6", "T7", "2 mã khác", "Cổ tức tiền",
      "Phí và thuế giao dịch", "Cuối kỳ"]);
    expect(bars[10].amount).toBe(3);  // 2 + 1
  });
  it("names the three largest causes other than money in and out", () => {
    expect(bridgeNotes(b)).toEqual(["Phí và thuế giao dịch làm giảm 50 đ", "T0 đóng góp 10 đ", "T1 đóng góp 9 đ"]);
  });
});

describe("barSpans", () => {
  it("stands totals on zero and chains each step from where the last ended", () => {
    expect(barSpans([{ amount: 100, kind: "total" }, { amount: 20, kind: "step" }, { amount: -50, kind: "step" }, { amount: 70, kind: "total" }]))
      .toEqual([[0, 100], [100, 120], [120, 70], [0, 70]]);
  });
});

describe("bridge with the book", () => {
  const b = { status: "ok" as const, month: "2026-12", start_day: "2026-11-30", end_day: "2026-12-31", start: "100", end: "110", other: "0",
    steps: [{ id: "ticker:FPT", symbol: "FPT", amount: "10" }] };
  const book = { status: "ok" as const, start: "1000", end: "1060", steps: [{ id: "book:fund_price", amount: "20" }, { id: "book:entries", amount: "40" }] };
  it("adds the book to the start and the end and lists its causes after the account", () => {
    const bars = bridgeBars(b, book);
    expect(bars.map((x) => [x.label, x.amount])).toEqual([["Đầu tháng", 1100], ["FPT", 10], ["Giá quỹ", 20], ["Sổ tài sản: ghi thêm/bớt/sửa", 40], ["Cuối kỳ", 1170]]);
    expect(barSpans(bars).at(-2)![1]).toBe(1170);  // the steps reach the end exactly
    expect(bridgeNotes(b, book)).toEqual(["Giá quỹ đóng góp 20 đ", "FPT đóng góp 10 đ"]);  // entries are money moved, not a cause
  });
});


describe("map tiles", () => {
  const tile = (id: string, value: string) => ({ id, label: id, note: null, value, change: null });
  it("puts the slivers of a crowded layer into one tile and leaves a short layer alone", () => {
    const out = mergeSmall([tile("a", "500"), tile("b", "300"), tile("c", "150"), tile("d", "20"), tile("e", "10"), tile("f", "10")]);
    expect(out.map((t) => t.label)).toEqual(["a", "b", "c", "3 khoản nhỏ"]);
    expect(out[3].value).toBe("40");
    expect(mergeSmall([tile("a", "500"), tile("b", "1")])).toHaveLength(2);
  });
  it("cuts a name to its tile with an ellipsis", () => {
    expect(fit("iPower TCBS (nhận lãi)", 100)).toBe("iPower TCBS…");
    expect(fit("KDH", 100)).toBe("KDH");
    expect(fit("KDH", 20)).toBe("");
  });
});
