import { expect, it } from "vitest";
import { matches } from "./screener-view";

const row = { symbol: "FPT", values: { verdict: "cheap", quality: null, chain: ["tailwind", "neutral"] }, missing: { quality: "Chưa có F-Score" } };

it("keeps a ticker when every chosen criterion has one of its chosen values, and never on missing data", () => {
  expect(matches({ verdict: ["cheap", "fair"] }, row)).toEqual({ ok: true, lacking: [] });
  expect(matches({ verdict: ["expensive"] }, row)).toEqual({ ok: false, lacking: [] });
  expect(matches({ chain: ["neutral"] }, row)).toEqual({ ok: true, lacking: [] });
  expect(matches({ verdict: ["cheap"], quality: ["strong"] }, row)).toEqual({ ok: false, lacking: ["quality"] });
  expect(matches({}, row)).toEqual({ ok: true, lacking: [] });
});
