import { describe, expect, it } from "vitest";
import { itemState } from "./year-end";

const item = (auto: boolean, done: boolean | null) => ({ id: "x", label: "x", auto, done, detail: null });

describe("Việc cuối năm", () => {
  it("says how each item stands and never counts an unreadable check as done", () => {
    expect(itemState(item(true, true))).toEqual({ text: "đã xong (tự kiểm)", tone: "good" });
    expect(itemState(item(true, false))).toEqual({ text: "chưa xong (tự kiểm)", tone: "warn" });
    expect(itemState(item(true, null))).toEqual({ text: "chưa kiểm được", tone: "" });
    expect(itemState(item(false, true))).toEqual({ text: "đã xong", tone: "good" });
    expect(itemState(item(false, false))).toEqual({ text: "chưa xong", tone: "warn" });
  });
});
