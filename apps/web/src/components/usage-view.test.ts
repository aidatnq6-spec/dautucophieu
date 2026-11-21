import { describe, expect, it } from "vitest";
import { pageLabel } from "./app-nav";
import { usageSince } from "./usage-view";

describe("Sử dụng phần mềm", () => {
  it("names a page by its menu label and keeps the path of a page outside the menu", () => {
    expect(pageLabel("/macro")).toBe("Vĩ mô");
    expect(pageLabel("/")).toBe("Tổng quan");
    expect(pageLabel("/research")).toBe("/research");
  });

  it("says since when visits are recorded, or that none are yet", () => {
    expect(usageSince({ pages: [], slow: [], slow_threshold: "1.0", since: "2026-11-21" })).toBe("Đã ghi từ 21/11/2026.");
    expect(usageSince({ pages: [], slow: [], slow_threshold: "1.0", since: null })).toBe("Chưa ghi lượt mở trang nào.");
  });
});
