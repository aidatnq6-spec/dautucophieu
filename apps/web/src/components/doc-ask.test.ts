import { describe, expect, it } from "vitest";
import { pageLink, spendText } from "./doc-ask";
import { proposalNote } from "./related-receivables";

describe("doc ask helpers", () => {
  it("links straight to a page and shows the month's spend", () => {
    expect(pageLink("https://a.vn/b.pdf#x", 38)).toBe("https://a.vn/b.pdf#page=38");
    expect(spendText({ month: "2026-11", used_usd: "0.0123", monthly_usd: "2" })).toBe("Đã dùng 0,0123 / 2 USD tháng 11/2026.");
  });
  it("says what the AI filled in and what it left out", () => {
    expect(proposalNote({ status: "ok", url: "u", cost_usd: "0.01", rows: [{ name: "Bên liên quan khác", amount: "2953", grouped: true, related: true,
      secured: false, interest: false, collect_within: null, page: 38 }], dropped: [{ name: "Công ty Bịa", reason: "amount_not_on_page" }] }))
      .toBe("Đã điền 1 dòng (trang 38): đọc lại từng dòng rồi mới lưu. Bỏ 1 dòng: Công ty Bịa (số dư không có trên trang AI ghi). Chi phí 0.01 USD.");
  });
});
