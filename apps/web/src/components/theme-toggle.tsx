"use client";
import { setThemeChoice, type ThemeChoice, useThemeChoice } from "../lib/theme";

const CHOICES: [ThemeChoice, string][] = [["light", "Sáng"], ["dark", "Tối"], ["system", "Theo máy"]];

export function ThemeToggle() {
  const current = useThemeChoice();
  return (
    <div className="theme-pick" role="group" aria-label="Giao diện">
      {CHOICES.map(([value, label]) => (
        <button key={value} type="button" aria-pressed={current === value} onClick={() => setThemeChoice(value)}>{label}</button>
      ))}
    </div>
  );
}
