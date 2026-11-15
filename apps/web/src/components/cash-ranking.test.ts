import { describe, expect, it } from "vitest";
import { ratioText, type CashRow } from "./cash-ranking";

const R: CashRow = { symbol: "AAA", sector: "Công nghệ Thông tin", quarter: "2026-Q3", cash_like: "500000000000", debt: "100000000000",
  net_cash: "400000000000", close: "20000", close_date: "2026-11-13", market_cap: "2000000000000", net_cash_to_cap: "0.2000", missing: null };

describe("ratioText", () => {
  it("shows net cash against market value as a percent, or says what is missing", () => {
    expect(ratioText(R)).toBe("20,0%");
    expect(ratioText({ ...R, net_cash_to_cap: "-0.4000" })).toBe("-40,0%");
    expect(ratioText({ ...R, net_cash_to_cap: null, missing: "shares" })).toBe("chưa có số cổ phiếu lưu hành");
  });
});
