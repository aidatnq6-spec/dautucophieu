import { describe, expect, it } from "vitest";
import { findSymbol, parse, plain } from "./assistant";

const SYMBOLS = ["FPT", "HPG", "VIC", "SSI", "KDH", "MBB"];

describe("assistant", () => {
  it("reads Vietnamese without accents", () => {
    expect(plain("  Sổ nào sắp ĐÁO HẠN? ")).toBe("so nao sap dao han?");
  });
  it("finds a watched ticker, but not a common word written in small letters", () => {
    expect(findSymbol("định giá hpg thế nào", SYMBOLS)).toBe("HPG");
    expect(findSymbol("SSI có sự kiện gì", SYMBOLS)).toBe("SSI");
    expect(findSymbol("lãi lỗ hôm nay", SYMBOLS)).toBeNull();
  });
  it("turns a question into what to show", () => {
    expect(parse("định giá HPG", SYMBOLS)).toEqual({ kind: "stock", symbol: "HPG", focus: "valuation" });
    expect(parse("FPT", SYMBOLS)).toEqual({ kind: "stock", symbol: "FPT", focus: "price" });
    expect(parse("cổ tức KDH", SYMBOLS)).toEqual({ kind: "stock", symbol: "KDH", focus: "events" });
    expect(parse("sổ nào sắp đáo hạn", SYMBOLS)).toEqual({ kind: "money_in" });
    expect(parse("hôm nay có gì cần để ý", SYMBOLS)).toEqual({ kind: "today" });
    expect(parse("lãi lỗ hôm nay", SYMBOLS)).toEqual({ kind: "portfolio" });
    expect(parse("bản tin", SYMBOLS)).toEqual({ kind: "report" });
    expect(parse("hệ thống có lỗi không", SYMBOLS)).toEqual({ kind: "health" });
  });
  it("opens a page by its name", () => {
    const go = parse("mở thác nước", SYMBOLS);
    expect(go.kind).toBe("go");
    expect(go.kind === "go" && go.matches[0].href).toBe("/portfolio");
    const fund = parse("quỹ mở", SYMBOLS);
    expect(fund.kind === "go" && fund.matches[0].href).toBe("/funds");
    expect(parse("xyz abc", SYMBOLS)).toEqual({ kind: "unknown" });
  });
});
