import { describe, expect, it } from "vitest";
import { peerCell, sortPeers } from "./peer-compare";

describe("peerCell", () => {
  it("writes each kind of figure as the ticker's own page does", () => {
    expect(peerCell("197850935535000", "money")).toBe("197.851");
    expect(peerCell("1.26", "x")).toBe("1,26x");
    expect(peerCell("0.2288", "pct")).toBe("22,9%");
    expect(peerCell("0.0071", "pct2")).toBe("0,71%");
    expect(peerCell("-0.2000", "pct")).toBe("-20,0%");
    expect(peerCell("6/9", "score")).toBe("6/9");
    expect(peerCell(null, "pct")).toBe("—");
  });
});

describe("sortPeers", () => {
  const rows = [{ symbol: "AAA", values: { pb: "1.20", quality: "6/9" } }, { symbol: "BBB", values: { pb: null, quality: "4/7" } },
    { symbol: "CCC", values: { pb: "0.90", quality: null } }];
  it("sorts by a column either way, a blank always last, and by name when no column is chosen", () => {
    expect(sortPeers(rows, "pb", "x", "asc").map((r) => r.symbol)).toEqual(["CCC", "AAA", "BBB"]);
    expect(sortPeers(rows, "pb", "x", "desc").map((r) => r.symbol)).toEqual(["AAA", "CCC", "BBB"]);
    expect(sortPeers(rows, "quality", "score", "desc").map((r) => r.symbol)).toEqual(["AAA", "BBB", "CCC"]);  // 6/9 before 4/7
    expect(sortPeers(rows, null, "x", "asc").map((r) => r.symbol)).toEqual(["AAA", "BBB", "CCC"]);
  });
});
