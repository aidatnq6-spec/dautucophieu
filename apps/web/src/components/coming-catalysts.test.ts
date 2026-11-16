import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";
import { describe, expect, it } from "vitest";
import { ComingTimeline, keyed } from "./coming-catalysts";

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
