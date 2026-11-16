import { describe, expect, it } from "vitest";
import { findingText } from "./related-receivables";

describe("findingText", () => {
  it("says a named party is no longer named, and the group that may hold it", () => {
    expect(findingText({ kind: "vanished", year: "2020", from_year: "2019", name: "Công ty Alpha", amount: "2820",
      group: { name: "Bên liên quan khác", amount: "2953" } }))
      .toBe("Công ty Alpha (2.820 tỷ năm 2019) không còn được nêu tên năm 2020; có thể đã nằm trong dòng gộp \"Bên liên quan khác\" (2.953 tỷ). "
        + "Đọc thuyết minh năm trước để biết đối tượng và hỏi khoản này đã thu chưa.");
  });
  it("says when a named supplier of prepayments is no longer named", () => {
    expect(findingText({ kind: "vanished", year: "2022", from_year: "2021", name: "Công ty Wang Sea", amount: "300", row_kind: "prepay",
      group: { name: "Các nhà cung cấp khác", amount: "1493" } }))
      .toContain("Công ty Wang Sea (nhà cung cấp được nêu tên trong thuyết minh trả trước) (300 tỷ năm 2021) không còn được nêu tên năm 2022");
  });
  it("names a balance not collected in its term and an unsecured interest-free one", () => {
    expect(findingText({ kind: "not_collected", year: "2020", name: "Công ty Gamma", before: "500", now: "400", promised: "12 tháng" }))
      .toBe("Công ty Gamma: hứa thu trong 12 tháng, nhưng năm 2020 vẫn còn 400 tỷ (năm trước 500 tỷ).");
    expect(findingText({ kind: "unsecured_free", year: "2020", name: "Công ty Gamma", amount: "400,5".replace(",", ".") }))
      .toBe("Công ty Gamma: phải thu bên liên quan 400,5 tỷ năm 2020, không có bảo đảm và không tính lãi.");
  });
});
