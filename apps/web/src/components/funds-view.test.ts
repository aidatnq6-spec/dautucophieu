import { describe, expect, it } from "vitest";
import { mineNotes, returnText } from "./funds-view";

describe("returnText", () => {
  it("shows a percentage return with its sign, and a dash when the source has none", () => {
    expect(returnText("-9.64")).toBe("−9,64%");
    expect(returnText("47.02")).toBe("+47,02%");
    expect(returnText("0")).toBe("0,00%");
    expect(returnText(null)).toBe("—");
  });
});

describe("mineNotes", () => {
  it("warns about too few funds, a single kind and funds counted at cost", () => {
    const notes = mineNotes({ groups: [{ kind: "BOND", value: "1000", share: "1", funds: ["VFF"] }], total: "1000", fund_count: 1, at_cost: ["GONE"],
      notes: ["fewer_than_3", "single_kind"] });
    expect(notes).toEqual(["Bạn đang giữ 1 quỹ: ít hơn 3 quỹ thì một quỹ đi sai hướng ảnh hưởng lớn đến cả phần quỹ.",
      "Toàn bộ nằm trong một nhóm (Trái phiếu): chưa có nhóm khác để cân lại khi thị trường đổi chiều.",
      "Chưa có NAV của GONE: tính theo vốn đã mua và chưa rõ nhóm."]);
    expect(mineNotes({ groups: [], total: "0", fund_count: 0, at_cost: [], notes: [] })).toEqual([]);
  });
});
