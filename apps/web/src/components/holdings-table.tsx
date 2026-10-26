import { formatRatio, formatVnd } from "../lib/format";
import { SCOPE_LABEL, label } from "./labels";

export type HoldingRow = { security_id: string; quantity: number; pending_quantity: number; total_cost: string; average_cost: string; price: string | null;
  price_date: string | null; market_value: string | null; unrealized_gain: string | null; weight_of_capital: string | null; scope: string;
  quality_status: string; blocked_by: string[] };

function Gain({ value }: { value: string | null }) {
  if (value === null) return <>—</>;
  const loss = value.startsWith("-");
  return <span className={loss ? "negative" : "positive"}>{loss ? "Lỗ " : "Lãi "}{formatVnd(value)}</span>;
}

export function HoldingsTable({ rows, showScope = true }: { rows: HoldingRow[]; showScope?: boolean }) {
  if (!rows.length) return <p className="muted">Chưa có cổ phiếu trong sổ.</p>;
  return (
    <div className="tablewrap">
      <table aria-label="Danh mục đang nắm giữ">
        <thead><tr><th>Mã</th><th className="num">Số lượng</th><th className="num">Giá vốn bình quân (đ/cp)</th><th className="num">Giá (ngày)</th>
          <th className="num">Giá trị</th><th className="num">Lãi/lỗ chưa thực hiện</th><th className="num">Tỷ trọng / vốn có thể đầu tư</th>{showScope && <th>Phạm vi</th>}</tr></thead>
        <tbody>{rows.map((r) => (
          <tr key={r.security_id} data-testid={`overview-${r.security_id}`}>
            <td><strong>{r.security_id}</strong></td>
            <td className="num">{r.quantity.toLocaleString("vi-VN")}{r.pending_quantity ? ` (+${r.pending_quantity.toLocaleString("vi-VN")} chờ về)` : ""}</td>
            <td className="num">{formatVnd(r.average_cost, { unit: false })}</td>
            <td className="num">{r.price ? `${formatVnd(r.price, { unit: false })} (${r.price_date})` : "Chưa có giá"}</td>
            <td className="num">{formatVnd(r.market_value)}</td>
            <td className="num"><Gain value={r.unrealized_gain} /></td>
            <td className="num">{formatRatio(r.weight_of_capital)}</td>
            {showScope && <td>{label(SCOPE_LABEL, r.scope)}{r.blocked_by.length ? " · có sự kiện chưa hỗ trợ" : ""}</td>}
          </tr>))}
        </tbody>
      </table>
    </div>
  );
}
