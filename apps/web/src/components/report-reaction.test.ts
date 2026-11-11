import { describe, expect, it } from "vitest";
import { summaryText } from "./report-reaction";

describe("summaryText", () => {
  it("counts the quarters where the price went against the news", () => {
    expect(summaryText({ compared: 8, good_sold: 3, bad_bought: 1, same_way: 4 }))
      .toBe("8 quý có đủ số: 3 lần lợi nhuận tăng mà giá giảm sau 20 phiên, 1 lần lợi nhuận giảm mà giá tăng, 4 lần giá đi cùng chiều lợi nhuận.");
    expect(summaryText({ compared: 0, good_sold: 0, bad_bought: 0, same_way: 0 })).toBe("Chưa có quý nào đủ ngày ra báo cáo và giá 20 phiên sau đó.");
  });
});
