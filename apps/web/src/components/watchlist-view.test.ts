import { describe, expect, it } from "vitest";
import { groupsCaption } from "./watchlist-view";

describe("groupsCaption", () => {
  it("dates each group, and says a kept VN100 list has no automatic source", () => {
    expect(groupsCaption({ groups_as_of: "2026-11-13", group_dates: { VN30: "2026-11-13", VN100: "2026-11-10" }, kept: ["VN100"] }))
      .toBe("Thành phần VN30: theo VNDirect ngày 13/11/2026; VN100: danh sách lưu ngày 10/11/2026 (chưa đọc được thông báo của HOSE, giữ danh sách cũ).");
    expect(groupsCaption({ groups_as_of: "2026-11-16", group_dates: { VN30: "2026-11-16", VN100: "2026-11-16" }, kept: [],
      group_sources: { VN100: { source: "hose", period: "10/2026", effective: "2026-11-16" } } }))
      .toBe("Thành phần VN30: theo VNDirect ngày 16/11/2026; VN100: theo thông báo HOSE kỳ 10/2026, hiệu lực 16/11/2026.");
    expect(groupsCaption({ groups_as_of: "2026-10-25" })).toBe("Thành phần VN30/VN100 theo nguồn ngày 2026-10-25.");
    expect(groupsCaption({ groups_as_of: null })).toBeNull();
  });
});
