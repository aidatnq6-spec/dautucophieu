import { describe, expect, it } from "vitest";
import { calendarWeeks, type Day, dayTone, monthCalendars } from "./daily-calendar";

const ok = (date: string, r: string): Day => ({ date, status: "ok", gain: "1", return: r, tickers: [] });

describe("daily calendar", () => {
  it("lays the sessions out a week per column, Monday first, leaving holidays empty", () => {
    const weeks = calendarWeeks([ok("2026-11-12", "0.01"), ok("2026-11-13", "0"), ok("2026-11-16", "-0.03")]);  // Thu, Fri, next Mon
    expect(weeks.length).toBe(2);
    expect(weeks[0].map((d) => d?.date ?? null)).toEqual([null, null, null, "2026-11-12", "2026-11-13"]);
    expect(weeks[1][0]?.date).toBe("2026-11-16");
  });
  it("colours by the day's return", () => {
    expect(dayTone(ok("2026-11-12", "0.01"))).toBe("dc-g2");
    expect(dayTone(ok("2026-11-12", "-0.03"))).toBe("dc-r3");
    expect(dayTone({ date: "2026-11-12", status: "missing", missing: ["X"] })).toBe("dc-none");
  });
});


describe("monthCalendars", () => {
  it("draws one month per block, newest first, with its total and its up and down sessions", () => {
    const g = (date: string, gain: string): Day => ({ date, status: "ok", gain, return: "0.01", tickers: [] });
    const out = monthCalendars([g("2026-10-30", "100"), g("2026-11-02", "300"), g("2026-11-03", "-50"), { date: "2026-11-04", status: "missing", missing: ["X"] }]);
    expect(out.map((m) => m.month)).toEqual(["2026-11", "2026-10"]);
    expect(out[0]).toMatchObject({ gain: 250, up: 1, down: 1, missing: 1 });
    expect(out[0].weeks[0].slice(0, 3).map((c) => (c && c !== "off" ? c.date : c))).toEqual(["2026-11-02", "2026-11-03", "2026-11-04"]);
    expect(out[1].weeks.at(-1)![4]).not.toBe("off");  // Friday 30/10 is in October's last week
  });
});
