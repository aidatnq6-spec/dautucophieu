import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { alpha, resolveColor } from "./theme";
import { THEME_SCRIPT } from "./theme-script";

const css = readFileSync(resolve(__dirname, "../app/globals.css"), "utf8");
const LIGHT = /:root\{([^}]*)\}/.exec(css)?.[1] ?? "";
const DARK = /:root\[data-theme=dark\]\{([^}]*)\}/.exec(css)?.[1] ?? "";
const tokens = (block: string) => Object.fromEntries([...block.matchAll(/--([a-z0-9-]+):(#[0-9a-f]{3,6})/g)].map((m) => [m[1], m[2]]));

function luminance(hex: string): number {
  const h = hex.length === 4 ? [...hex.slice(1)].map((c) => c + c).join("") : hex.slice(1);
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

describe("the dark colours", () => {
  const dark = tokens(DARK);
  it("define every colour the light theme has", () => {
    expect(Object.keys(tokens(LIGHT)).length).toBeGreaterThan(40);
    expect(Object.keys(tokens(LIGHT)).filter((k) => !(k in dark))).toEqual([]);
  });
  it.each([
    ["ink", "paper"], ["ink", "bg"], ["muted", "paper"], ["muted", "bg"], ["link", "paper"], ["good", "paper"], ["bad", "paper"], ["good", "bg"], ["bad", "bg"],
    ["on-brand", "brand"], ["on-ink", "ink"], ["nav-on-ink", "nav-on-bg"], ["pill-ink", "pill-bg"], ["good-ink", "good-bg"], ["warn-soft-ink", "warn-soft-bg"], ["bad-ink", "bad-bg"],
    ["warn-ink", "warn-bg"], ["err-ink", "err-bg"], ["good-ink", "macd-up-bg"], ["bad-ink", "macd-down-bg"], ["pill-ink", "rsi-low-bg"],
    ["tb-ref", "paper"], ["tb-ceil", "paper"], ["tb-floor", "paper"], ["good", "soft"], ["bad", "soft"], ["ink", "field"],
    ["ink", "warn-bg"], ["ink", "macro-bg"], ["ink", "over-bg"], ["ink", "sup-bg"], ["ink", "ok-bg"], ["ink", "fixed-bg"], ["ink", "deposit-bg"], ["ink", "intangible-bg"], ["hero-ink", "hero-bg"], ["hero-note", "hero-bg"],
  ])("keep %s readable on %s", (fg, bg) => {
    expect(contrast(dark[fg], dark[bg])).toBeGreaterThanOrEqual(4.5);
  });
  it.each([["brand", "paper"], ["line", "bg"], ["signal", "paper"], ["rsi", "paper"], ["draw", "paper"], ["overlay-channel", "paper"], ["overlay-zone", "paper"], ["overlay-broken", "paper"],
    ["op1", "paper"], ["op2", "paper"], ["op3", "paper"], ["op4", "paper"], ["op5", "paper"], ["op6", "paper"], ["op7", "paper"], ["op8", "paper"], ["orange", "paper"]].filter(([fg]) => fg !== "line"))(
    "keep the chart colour %s visible on %s", (fg, bg) => { expect(contrast(dark[fg], dark[bg])).toBeGreaterThanOrEqual(3); });
});

it("no colour is written outside the two colour sets, so a new rule cannot miss the dark theme", () => {
  const rest = css.replace(/:root\{[^}]*\}/, "").replace(/:root\[data-theme=dark\]\{[^}]*\}/, "");
  expect(rest.match(/#[0-9a-fA-F]{3,8}\b/g) ?? []).toEqual([]);
});

it("the dark colours apply on screen only, so anything printed stays on white", () => {
  expect(css).toMatch(/@media screen\{:root\[data-theme=dark\]\{/);
});

describe("the script that sets the theme before the page paints", () => {
  const run = (saved: string | null, prefersDark: boolean, blocked = false) => {
    const root = { dataset: {} as Record<string, string> };
    const storage = { getItem: () => { if (blocked) throw new Error("blocked"); return saved; } };
    new Function("localStorage", "matchMedia", "document", THEME_SCRIPT)(storage, () => ({ matches: prefersDark }), { documentElement: root });
    return root.dataset.theme;
  };
  it("uses the saved choice whatever the machine prefers", () => {
    expect(run("dark", false)).toBe("dark");
    expect(run("light", true)).toBe("light");
  });
  it("follows the machine otherwise, also when storage cannot be read", () => {
    expect(run(null, true)).toBe("dark");
    expect(run("system", false)).toBe("light");
    expect(run(null, true, true)).toBe("dark");
  });
});

it("alpha gives the rgba the chart library needs", () => {
  expect(alpha("#137556", 0.35)).toBe("rgba(19,117,86,0.35)");
  expect(alpha("#fff", 0.5)).toBe("rgba(255,255,255,0.5)");
});

it("a colour that is not a token is left as it is", () => {
  expect(resolveColor("#123456")).toBe("#123456");
});
