import { describe, expect, it } from "vitest";
import { filterEntries, filterLedger, NO_FILTER, spreadsheet, summarize, type JournalRow } from "./journal-tools";

const entry = (over: Partial<JournalRow>): JournalRow => ({ symbol: "FPT", kind: "buy", created_on: "2026-01-10", reason: "", emotion: null, emotion_note: "", notes: [],
  change: null, imported: null, ...over });
const rows = [entry({ symbol: "HPG", created_on: "2025-03-01", reason: "Định giá RẺ", emotion: "fomo", change: "-0.1000" }),
  entry({ symbol: "FPT", kind: "sell", created_on: "2026-05-01", emotion: "fomo", change: "0.3000", notes: [{ on: "2026-06-01", text: "bán sớm quá" }] }),
  entry({ symbol: "BDS", created_on: "2024-01-01", reason: "Đất", imported: { asset: "Bất động sản", ticker: "Đất", qty: null, price: null, total: "100", pnl: null } }),
  entry({ symbol: "HPG", kind: "sell", created_on: "2025-06-01", imported: { asset: "Cổ phiếu", ticker: "HPG", qty: "1", price: "1", total: "1", pnl: "-500" } })];

describe("filterEntries", () => {
  const symbols = (f: Partial<typeof NO_FILTER>) => filterEntries(rows, { ...NO_FILTER, ...f }).map((r) => r.created_on);
  it("puts the newest decision first, whatever order the entries were saved in", () => {
    expect(symbols({})).toEqual(["2026-05-01", "2025-06-01", "2025-03-01", "2024-01-01"]);
  });
  it("narrows by ticker, order, emotion, asset and a date range", () => {
    expect(symbols({ symbol: "hp" })).toEqual(["2025-06-01", "2025-03-01"]);
    expect(symbols({ kind: "sell" })).toEqual(["2026-05-01", "2025-06-01"]);
    expect(symbols({ emotion: "fomo" })).toEqual(["2026-05-01", "2025-03-01"]);
    expect(symbols({ asset: "Bất động sản" })).toEqual(["2024-01-01"]);
    expect(symbols({ from: "2025-03-01", to: "2025-06-01" })).toEqual(["2025-06-01", "2025-03-01"]);
  });
  it("finds a word in the reason or a later note, with or without accents", () => {
    expect(symbols({ text: "dinh gia re" })).toEqual(["2025-03-01"]);
    expect(symbols({ text: "BÁN SỚM" })).toEqual(["2026-05-01"]);
  });
});

describe("summarize", () => {
  it("averages the price change only over entries that have one, and adds only the profit typed into imported sales", () => {
    const all = summarize(rows);
    expect(all.average).toBeCloseTo(0.1, 10);
    expect({ ...all, average: 0 }).toEqual({ count: 4, average: 0, withChange: 2, pnl: -500, withPnl: 1 });
    expect(summarize([rows[2]])).toEqual({ count: 1, average: null, withChange: 0, pnl: null, withPnl: 0 });
  });
});

describe("filterLedger", () => {
  const events = [{ effective_at: "2026-01-05T00:00:00", type: "buy", security_id: "FPT" }, { effective_at: "2026-03-05", type: "sell", security_id: "HPG" },
    { effective_at: "2026-04-05", type: "deposit" }];
  it("narrows by ticker, type and days", () => {
    expect(filterLedger(events, { symbol: "fp", type: "", from: "", to: "" })).toHaveLength(1);
    expect(filterLedger(events, { symbol: "", type: "deposit", from: "", to: "" })).toHaveLength(1);
    expect(filterLedger(events, { symbol: "", type: "", from: "2026-01-05", to: "2026-03-05" })).toHaveLength(2);
  });
});

describe("spreadsheet", () => {
  it("writes typed Excel cells, escaped so text can never act as a formula or as markup", () => {
    const xml = spreadsheet("NhatKy", ["Mã", "SL"], [["=1+1 <b>&", 1000], [null, "x"]]);
    expect(xml).toContain('<Data ss:Type="String">=1+1 &lt;b&gt;&amp;</Data>');
    expect(xml).toContain('<Data ss:Type="Number">1000</Data>');
    expect(xml).toContain('<Data ss:Type="String"></Data>');
    expect(xml.startsWith("<?xml")).toBe(true);
  });
});
