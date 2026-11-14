import { describe, expect, it } from "vitest";
import { calendarWeeks, type Day, dayTone } from "./daily-calendar";

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
