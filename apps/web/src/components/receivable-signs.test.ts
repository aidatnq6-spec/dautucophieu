import { describe, expect, it } from "vitest";
import { parts } from "./receivable-signs";

const SIGNS = [{ key: "a", title: "Phải thu khác lớn" }, { key: "b", title: "Thu nhập trên giấy" }, { key: "c", title: "Trả trước tăng" }];

describe("parts", () => {
  it("lists the signs that are on with their figures, and names those that could not be read", () => {
    const row = { symbol: "VCG", sector: "Xây dựng", signs: { a: true, b: null, c: false }, count: 1, details: { a: "8.451 tỷ, 27,0% tổng tài sản" } };
    expect(parts(row, SIGNS)).toEqual({ on: [{ key: "a", title: "Phải thu khác lớn", detail: "8.451 tỷ, 27,0% tổng tài sản" }], missing: ["Thu nhập trên giấy"] });
  });
  it("weighs only the signs a row has: a bank is not missing the non-financial ones", () => {
    const bank = { symbol: "VCB", sector: "Ngân hàng", signs: { c: null }, count: 0, details: {} };
    expect(parts(bank, SIGNS)).toEqual({ on: [], missing: ["Trả trước tăng"] });
  });
});
