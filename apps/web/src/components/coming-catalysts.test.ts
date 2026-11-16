import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";
import { describe, expect, it } from "vitest";
import { ComingTimeline, grouped, keyed } from "./coming-catalysts";

const item = (symbol: string, id: string, on: string | null, extra = {}) =>
  ({ symbol, id, when: "", on, sign: "?" as const, text: `${symbol} ${id}`, source: "", done: false, auto: false, due: false, ...extra });

describe("coming catalysts", () => {
  it("keeps two tickers' catalysts apart even with the same id", () => {
    expect(keyed([item("PHP", "c1", null), item("FPT", "c1", null)]).map((c) => c.id)).toEqual(["PHP:c1", "FPT:c1"]);
  });
  it("shows each catalyst's ticker as a link and marks the overdue ones", () => {
    const html = renderToStaticMarkup(createElement(ComingTimeline, {
      items: [item("PHP", "c1", "2027-01-10", { due: true }), item("FPT", "e1", "2027-01-20", { auto: true })], today: "2027-01-15" }));
    expect(html).toContain('href="/research/PHP"');
    expect(html).toContain('href="/research/FPT"');
    expect(html.match(/đã đến mốc/g)).toHaveLength(1);
    expect(html).toContain("tự động");
  });
});

describe("report deadlines of the same day", () => {
  const report = (symbol: string, on = "2027-01-20") => item(symbol, `r-${symbol}`, on, { auto: true, when: "Q4/2026", source: "Thông tư 96/2020 Điều 14",
    text: "Hạn công bố báo cáo tài chính Q4/2026 (20 ngày sau khi hết quý)" });
  it("become one line naming how many tickers, the tickers behind a toggle", () => {
    const out = grouped([report("PHP"), report("FPT"), report("HPG"), item("FPT", "c1", "2027-01-20")]);
    expect(out).toHaveLength(2);
    const one = out.find((c) => c.symbols)!;
    expect(one.symbols).toEqual(["FPT", "HPG", "PHP"]);
    expect(one.text).toBe("Hạn công bố báo cáo tài chính Q4/2026 của 3 mã (20 ngày sau khi hết quý)");
    const html = renderToStaticMarkup(createElement(ComingTimeline, { items: [report("PHP"), report("FPT")], today: "2027-01-15" }));
    expect(html).toContain("2 mã");
    expect(html).toContain("Xem 2 mã");
    expect(html).toContain('href="/research/PHP"');
  });
  it("a single ticker's deadline stays as it is", () => {
    expect(grouped([report("PHP"), report("FPT", "2027-01-21")]).every((c) => !c.symbols)).toBe(true);
  });
});
