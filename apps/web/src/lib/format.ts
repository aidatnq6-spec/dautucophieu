/** Display helpers for decimal strings from the API. Never parse money through binary floats. */

export function formatVnd(value: string | null | undefined, { unit = true }: { unit?: boolean } = {}): string {
  if (value === null || value === undefined || value === "") return "—";
  const negative = value.startsWith("-");
  const [intPart, frac = ""] = (negative ? value.slice(1) : value).split(".");
  // Round half up to whole VND on the decimal string itself.
  let digits = intPart.replace(/^0+(?=\d)/, "");
  if (frac && frac[0] >= "5") digits = (BigInt(digits) + BigInt(1)).toString();
  const grouped = digits.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const sign = negative && grouped !== "0" ? "−" : "";
  return `${sign}${grouped}${unit ? " đ" : ""}`;
}

export function formatRatio(value: string | null | undefined, digits = 1): string {
  if (value === null || value === undefined || value === "") return "—";
  const negative = value.startsWith("-");
  const [i, f = ""] = (negative ? value.slice(1) : value).split(".");
  const scaled = (i + (f + "0000").slice(0, 2 + digits)).replace(/^0+(?=\d)/, "");
  const whole = (scaled.slice(0, -digits) || "0").replace(/^0+(?=\d)/, "");
  const frac = scaled.slice(-digits).padStart(digits, "0");
  const sign = negative && /[1-9]/.test(whole + frac) ? "−" : "";
  return `${sign}${whole},${frac}%`;
}

/** Calendar date (YYYY-MM-DD) in Asia/Ho_Chi_Minh, the timezone of trading sessions. */
export function hanoiDate(at: Date = new Date()): string {
  return at.toLocaleDateString("sv-SE", { timeZone: "Asia/Ho_Chi_Minh" });
}

/** Accept "500.000.000", "500 000 000" or "1234,5" from inputs; returns a canonical decimal string or null. */
export function parseMoneyInput(raw: string): string | null {
  const cleaned = raw.trim().replace(/[\s.]/g, "").replace(",", ".");
  if (!/^(0|[1-9]\d*)(\.\d+)?$/.test(cleaned)) return null;
  return cleaned;
}

/** "0,15" (percent) → "0.0015" (ratio), by moving the decimal point on the string; null when invalid or above 100%. */
export function percentToRatio(raw: string): string | null {
  const v = parseMoneyInput(raw);
  if (v === null) return null;
  const [i, f = ""] = v.split(".");
  const digits = (i.padStart(3, "0") + f);
  const whole = digits.slice(0, digits.length - f.length - 2).replace(/^0+(?=\d)/, "") || "0";
  const frac = (digits.slice(digits.length - f.length - 2)).replace(/0+$/, "");
  if (Number(whole) > 1 || (whole === "1" && frac)) return null;
  return frac ? `${whole}.${frac}` : whole;
}
