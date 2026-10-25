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
  const [i, f = ""] = value.split(".");
  const scaled = (i + (f + "0000").slice(0, 2 + digits)).replace(/^0+(?=\d)/, "");
  const whole = scaled.slice(0, -digits) || "0";
  return `${whole.replace(/^0+(?=\d)/, "")},${scaled.slice(-digits)}%`;
}

/** Accept "500.000.000", "500 000 000" or "1234,5" from inputs; returns a canonical decimal string or null. */
export function parseMoneyInput(raw: string): string | null {
  const cleaned = raw.trim().replace(/[\s.]/g, "").replace(",", ".");
  if (!/^(0|[1-9]\d*)(\.\d+)?$/.test(cleaned)) return null;
  return cleaned;
}
