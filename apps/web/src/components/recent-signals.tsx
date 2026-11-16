export type SignalRow = { date: string; change: string | null; pct: string | null; known: boolean; breadth: string | null;
  low_liquidity: boolean | null; ratio20: string | null; asia: string | null; asia_counted: number | null; top: { symbol: string; points: string } | null };

const dm = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}`;
const signed = (v: string | number, d = 2) => `${Number(v) > 0 ? "+" : Number(v) < 0 ? "−" : ""}${Math.abs(Number(v)).toLocaleString("vi-VN", { minimumFractionDigits: d, maximumFractionDigits: d })}`;
const BREADTH: Record<string, string> = { green_over_red: "xanh vỏ đỏ lòng", red_over_green: "đỏ vỏ xanh lòng" };
const ASIA: Record<string, string> = { with: "cùng chiều", against: "ngược chiều", split: "chia đôi" };

/** How many sessions in a row, from the newest back, each signal has held; a session without signals ends the count and is said. */
export function runs(rows: SignalRow[]): string | null {
  const count = (test: (r: SignalRow) => boolean) => { let n = 0; for (const r of rows) { if (!r.known || !test(r)) break; n++; } return n; };
  const parts: string[] = [];
  const add = (label: string, n: number) => { if (n > 0) parts.push(`${label} ${n} phiên${n > 1 ? " liền" : ""}`); };
  add("xanh vỏ đỏ lòng", count((r) => r.breadth === "green_over_red"));
  add("đỏ vỏ xanh lòng", count((r) => r.breadth === "red_over_green"));
  add("thanh khoản thấp", count((r) => r.low_liquidity === true));
  add("ngược chiều châu Á", count((r) => r.asia === "against"));
  if (!parts.length) return null;
  const stopped = rows.findIndex((r) => !r.known);
  return `Chuỗi đang chạy: ${parts.join(" · ")}${stopped > 0 ? " (phiên trước chưa có số tín hiệu)" : ""}.`;
}

/** 5 phiên gần nhất: each session's VN-Index move and signals, newest first, to see runs of days. */
export function RecentSignals({ rows }: { rows: SignalRow[] }) {
  if (!rows.length) return null;
  const run = runs(rows);
  return (
    <section aria-label="5 phiên gần nhất" data-testid="recent-signals">
      <h3>5 phiên gần nhất</h3>
      <div className="tablewrap"><table className="fv-table" aria-label="Tín hiệu 5 phiên gần nhất">
        <thead><tr><th>Phiên</th><th className="num">VN-Index</th><th>Độ rộng</th><th>Thanh khoản (so TB20)</th><th>Châu Á</th><th>Mã kéo nhiều nhất</th></tr></thead>
        <tbody>{rows.map((r) => <tr key={r.date}>
          <td>{dm(r.date)}</td>
          <td className="num">{r.change !== null ? `${signed(r.change)} điểm` : "—"}</td>
          {r.known ? <>
            <td>{r.breadth ? <span className="pill bad">{BREADTH[r.breadth]}</span> : "bình thường"}</td>
            <td>{r.ratio20 !== null ? <>{Math.round(Number(r.ratio20) * 100)}%{r.low_liquidity && <> <span className="pill warn">thấp</span></>}</> : "—"}</td>
            <td>{r.asia ? `${ASIA[r.asia]} (${r.asia_counted} thị trường)` : "—"}</td>
            <td>{r.top ? `${r.top.symbol} ${signed(r.top.points)} điểm` : "—"}</td>
          </> : <td colSpan={4} className="muted">chưa có số tín hiệu (ảnh chụp trước 16/11/2026)</td>}
        </tr>)}</tbody>
      </table></div>
      {run && <p data-testid="signal-runs"><strong>{run}</strong></p>}
    </section>
  );
}
