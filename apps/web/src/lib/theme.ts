import { useSyncExternalStore } from "react";
import { THEME_KEY } from "./theme-script";

export type ThemeChoice = "light" | "dark" | "system";

const listeners = new Set<() => void>();
const media = () => window.matchMedia("(prefers-color-scheme: dark)");

function savedChoice(): ThemeChoice {
  try {
    const s = localStorage.getItem(THEME_KEY);
    return s === "light" || s === "dark" ? s : "system";
  } catch {
    return "system";
  }
}

function apply() {
  const choice = savedChoice();
  document.documentElement.dataset.theme = choice === "dark" || (choice === "system" && media().matches) ? "dark" : "light";
  listeners.forEach((l) => l());
}

export function setThemeChoice(choice: ThemeChoice) {
  try {
    if (choice === "system") localStorage.removeItem(THEME_KEY);
    else localStorage.setItem(THEME_KEY, choice);
  } catch { /* storage blocked: the choice lasts until the page is reloaded */ }
  apply();
}

function subscribe(listener: () => void) {
  if (listeners.size === 0) {
    media().addEventListener("change", apply);
    window.addEventListener("storage", apply);
  }
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0) {
      media().removeEventListener("change", apply);
      window.removeEventListener("storage", apply);
    }
  };
}

export const useThemeChoice = () => useSyncExternalStore(subscribe, savedChoice, () => "system" as ThemeChoice);
/** The colours in force. Charts drawn by a library cannot use CSS variables, so they are rebuilt when this changes. */
export const useTheme = () => useSyncExternalStore(subscribe, () => (document.documentElement.dataset.theme === "dark" ? "dark" : "light"), () => "light");

/** A "var(--x)" token's current value, for a library that takes only real colours; anything else comes back unchanged. */
export function resolveColor(color: string): string {
  const name = /^var\((--[a-z0-9-]+)\)$/.exec(color)?.[1];
  return name ? getComputedStyle(document.documentElement).getPropertyValue(name).trim() : color;
}

export function alpha(hex: string, a: number): string {
  const h = hex.length === 4 ? [...hex.slice(1)].map((c) => c + c).join("") : hex.slice(1);
  return `rgba(${parseInt(h.slice(0, 2), 16)},${parseInt(h.slice(2, 4), 16)},${parseInt(h.slice(4, 6), 16)},${a})`;
}
