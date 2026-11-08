/** Finding things in Nhật ký and Sổ giao dịch, and handing them to Excel. Pure functions; nothing here leaves the browser. */

export type Imported = { asset: string; ticker: string; qty: string | null; price: string | null; total: string | null; pnl: string | null };
export type JournalRow = { symbol: string; kind: string; created_on: string; reason: string; emotion: string | null; emotion_note: string;
  notes: { on: string; text: string }[]; change: string | null; imported?: Imported | null };
export type JournalFilter = { symbol: string; kind: string; emotion: string; asset: string; text: string; from: string; to: string };
export const NO_FILTER: JournalFilter = { symbol: "", kind: "", emotion: "", asset: "", text: "", from: "", to: "" };

const fold = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase();

export function filterEntries<T extends JournalRow>(rows: T[], f: JournalFilter): T[] {
  const symbol = f.symbol.trim().toUpperCase(), text = fold(f.text.trim());
  return rows.filter((r) => (!symbol || r.symbol.includes(symbol) || (r.imported?.ticker ?? "").toUpperCase().includes(symbol))
    && (!f.kind || r.kind === f.kind) && (!f.emotion || r.emotion === f.emotion)
    && (!f.asset || (r.imported?.asset ?? "Cổ phiếu") === f.asset)
    && (!f.from || r.created_on >= f.from) && (!f.to || r.created_on <= f.to)
    && (!text || fold([r.reason, r.emotion_note, ...r.notes.map((n) => n.text)].join(" ")).includes(text)))
    .sort((a, b) => (a.created_on < b.created_on ? 1 : a.created_on > b.created_on ? -1 : 0));
}

export function summarize(rows: JournalRow[]) {
  const moves = rows.filter((r) => r.change !== null).map((r) => Number(r.change));
  const typed = rows.filter((r) => r.imported?.pnl != null).map((r) => Number(r.imported!.pnl));
  return { count: rows.length, average: moves.length ? moves.reduce((a, b) => a + b, 0) / moves.length : null, withChange: moves.length,
    pnl: typed.length ? typed.reduce((a, b) => a + b, 0) : null, withPnl: typed.length };
}

export type LedgerFilter = { symbol: string; type: string; from: string; to: string };
export function filterLedger<T extends { effective_at: string; type: string; security_id?: string | null }>(events: T[], f: LedgerFilter): T[] {
  const symbol = f.symbol.trim().toUpperCase();
  return events.filter((e) => (!symbol || (e.security_id ?? "").includes(symbol)) && (!f.type || e.type === f.type)
    && (!f.from || e.effective_at.slice(0, 10) >= f.from) && (!f.to || e.effective_at.slice(0, 10) <= f.to));
}

const escape = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const excelCell = (v: string | number | null | undefined) => (typeof v === "number" && Number.isFinite(v)
  ? `<Cell><Data ss:Type="Number">${v}</Data></Cell>`
  : `<Cell><Data ss:Type="String">${escape(v === null || v === undefined ? "" : String(v))}</Data></Cell>`);

/** Excel 2003 XML: every cell typed, so a reason starting with "=" stays text; opens without a separator or encoding problem. */
export function spreadsheet(name: string, headers: string[], rows: (string | number | null | undefined)[][]): string {
  const line = (cells: (string | number | null | undefined)[]) => `<Row>${cells.map(excelCell).join("")}</Row>\n`;
  return '<?xml version="1.0"?>\n<?mso-application progid="Excel.Sheet"?>\n<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" '
    + `xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">\n<Worksheet ss:Name="${escape(name)}">\n<Table>\n${line(headers)}${rows.map(line).join("")}</Table>\n</Worksheet>\n</Workbook>`;
}

export function download(xml: string, filename: string) {
  const url = URL.createObjectURL(new Blob([xml], { type: "application/vnd.ms-excel" }));
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
