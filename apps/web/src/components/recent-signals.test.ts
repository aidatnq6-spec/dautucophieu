import { describe, expect, it } from "vitest";
import { runs } from "./recent-signals";

const row = (date: string, o: Partial<{ breadth: string | null; low_liquidity: boolean | null; asia: string | null; known: boolean }>) =>
  ({ date, change: "1", pct: "0.001", known: true, breadth: null, low_liquidity: false, ratio20: "0.9", asia: null, asia_counted: null, top: null, ...o });

describe("runs", () => {
  it("counts each signal's run of sessions from the newest one back", () => {
    const rows = [row("2026-11-20", { breadth: "green_over_red", low_liquidity: true, asia: "against" }),
      row("2026-11-19", { breadth: "green_over_red", low_liquidity: true, asia: "with" }),
      row("2026-11-18", { low_liquidity: true }), row("2026-11-17", { breadth: "green_over_red" })];
    expect(runs(rows)).toBe("Chuỗi đang chạy: xanh vỏ đỏ lòng 2 phiên liền · thanh khoản thấp 3 phiên liền · ngược chiều châu Á 1 phiên.");
  });
  it("says nothing runs when the newest session had no signal, and stops at a session without signals", () => {
    expect(runs([row("2026-11-20", {}), row("2026-11-19", { low_liquidity: true })])).toBeNull();
    expect(runs([row("2026-11-16", { low_liquidity: true }), row("2026-11-13", { known: false, low_liquidity: null })]))
      .toBe("Chuỗi đang chạy: thanh khoản thấp 1 phiên (phiên trước chưa có số tín hiệu).");
  });
});
