import { describe, expect, it } from "vitest";
import { groupsCaption } from "./watchlist-view";

describe("groupsCaption", () => {
  it("dates each group, and says a kept VN100 list has no automatic source", () => {
    expect(groupsCaption({ groups_as_of: "2026-11-13", group_dates: { VN30: "2026-11-13", VN100: "2026-11-10" }, kept: ["VN100"] }))
      .toBe("Thành phần VN30: theo VNDirect ngày 13/11/2026; VN100: danh sách lưu ngày 10/11/2026 (không có nguồn tự động, cập nhật tay sau mỗi kỳ HOSE xét lại rổ).");
    expect(groupsCaption({ groups_as_of: "2026-10-25" })).toBe("Thành phần VN30/VN100 theo nguồn ngày 2026-10-25.");
    expect(groupsCaption({ groups_as_of: null })).toBeNull();
  });
});
