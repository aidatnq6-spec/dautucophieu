import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";
import { describe, expect, it } from "vitest";
import { CatalystTimeline, daysText, timeline } from "./catalyst-timeline";

const c = (id: string, on: string | null, done = false) => ({ id, when: "", on, sign: "?" as const, text: id, source: "", done });

describe("timeline", () => {
  it("puts the nearest coming events first, undated after them and what happened last", () => {
    const out = timeline([c("late", "2027-10-22"), c("done", "2026-11-01", true), c("none", null), c("soon", "2027-01-20")], "2026-11-14");
    expect(out.map((x) => x.id)).toEqual(["soon", "late", "none", "done"]);
    expect(out[0].days).toBe(67);
  });
  it("says how far away an event is", () => {
    expect(daysText(67, false)).toBe("còn 67 ngày");
    expect(daysText(0, false)).toBe("hôm nay");
    expect(daysText(-3, false)).toBe("đã qua 3 ngày");
    expect(daysText(5, true)).toBe("đã xảy ra");
  });
});

describe("CatalystTimeline as an editor", () => {
  it("names the list, marks a catalyst whose day has come and puts each one's buttons beside it", () => {
    const html = renderToStaticMarkup(createElement(CatalystTimeline, {
      items: [c("a", "2026-11-10"), c("b", "2027-01-20")], today: "2026-11-14", label: "Mốc và chất xúc tác", due: ["a"],
      actions: (x: { id: string }) => createElement("button", { type: "button" }, `Sửa ${x.id}`),
    }));
    expect(html).toContain('aria-label="Mốc và chất xúc tác"');
    expect(html.match(/đã đến mốc/g)).toHaveLength(1);
    expect(html).toContain("Sửa a");
    expect(html).toContain("Sửa b");
  });
});
