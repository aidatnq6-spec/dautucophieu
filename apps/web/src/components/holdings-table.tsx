import { formatVnd } from "../lib/format";

export type HoldingRow = { security_id: string; quantity: number; pending_quantity: number; total_cost: string; average_cost: string; price: string | null;
  price_date: string | null; market_value: string | null; unrealized_gain: string | null; weight_of_capital: string | null; scope: string;
  quality_status: string; blocked_by: string[] };

function SignedGain({ value }: { value: string | null }) {
  if (value === null) return <>—</>;
  const sign = value.startsWith("-") ? "−" : Number(value) > 0 ? "+" : "";
  return <span className={sign === "−" ? "negative" : sign ? "positive" : ""}>{sign}{formatVnd(value.replace(/^-/, ""))}</span>;
}

/** Held stocks in compact form (after-close brief and Tổng quan): signed coloured gains, no weight or scope column, no horizontal scroller. */
export function HoldingsTable({ rows }: { rows: HoldingRow[] }) {
  if (!rows.length) return <p className="muted">Chưa có cổ phiếu trong sổ.</p>;
  return (
    <table aria-label="Danh mục đang nắm giữ" className="fv-table brief-holdings">
      <thead><tr><th>Mã</th><th className="num">Số lượng</th><th className="num">Giá vốn bình quân (đ/cp)</th><th className="num">Giá (ngày)</th>
        <th className="num">Giá trị</th><th className="num">Lãi/lỗ chưa thực hiện</th></tr></thead>
      <tbody>{rows.map((r) => (
        <tr key={r.security_id} data-testid={`holding-${r.security_id}`}>
          <td data-label="Mã"><strong>{r.security_id}</strong></td>
          <td data-label="Số lượng" className="num">{r.quantity.toLocaleString("vi-VN")}{r.pending_quantity ? ` (+${r.pending_quantity.toLocaleString("vi-VN")} chờ về)` : ""}</td>
          <td data-label="Giá vốn bình quân" className="num">{formatVnd(r.average_cost, { unit: false })}</td>
          <td data-label="Giá (ngày)" className="num">{r.price ? `${formatVnd(r.price, { unit: false })} (${r.price_date})` : "Chưa có giá"}</td>
          <td data-label="Giá trị" className="num">{formatVnd(r.market_value)}</td>
          <td data-label="Lãi/lỗ chưa thực hiện" className="num gain"><SignedGain value={r.unrealized_gain} /></td>
        </tr>))}
      </tbody>
    </table>
  );
}
