import { expect, it } from "vitest";
import { nextSequence } from "./transaction-form";

it("numbers a new line after the highest on its day, not after the count (a cancelled line leaves a gap)", () => {
  const events = [{ event_id: "a", type: "buy", effective_at: "2026-06-09", sequence: 1 }, { event_id: "b", type: "buy", effective_at: "2026-06-10", sequence: 0 }];
  expect(nextSequence(events, "2026-06-09")).toBe(2);
  expect(nextSequence(events, "2026-06-11")).toBe(0);
});
