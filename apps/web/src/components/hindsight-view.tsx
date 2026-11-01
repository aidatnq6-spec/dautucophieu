"use client";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatDecimal } from "../lib/format";

type Horizon = { status: "ok" | "not_yet" | "missing"; on: string; change: string | null; index: string | null; diff: string | null };
type Trade = { event_id: string; symbol: string; type: "buy" | "sell"; date: string; price: string; quantity: number; horizons: Record<string, Horizon> };
type LossHold = { symbol: string; start: string; end: string | null; days: number | null; deepest: string; outcome: "recovered" | "sold_at_loss" | "holding" };
type Break = { symbol: string; kind: string; broken_on: string; broken_price: string; held_on: boolean; then: string | null; then_on: string | null;
  how: string; change: string | null };
type Group = { key: string; count: number; enough: boolean; mean: string | null; mean_diff: string | null };
type Data = { trades: Trade[]; opening_skipped: number; loss_holds: LossHold[]; breaks: Break[]; threshold: string;
  biases: { disposition: { days: number; pgr: string | null; plr: string | null; enough: boolean }; by_emotion: Group[]; by_reason: Group[];
    chasing: { chasing: Group; other: Group } } };

const day = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;
const pct = (ratio: string) => {
  const v = Number(ratio) * 100;
  return `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v).toFixed(1).replace(".", ",")}%`;
};
const EMOTION: Record<string, string> = { calm: "Bình tĩnh", excited: "Hào hứng", fomo: "Sợ bỏ lỡ (FOMO)", anxious: "Lo lắng", panic: "Hoảng sợ", regret: "Tiếc nuối" };
const REASON: Record<string, string> = { cheap: "Giá rẻ so với định giá", earnings: "Kết quả kinh doanh tốt", trend: "Xu hướng giá đẹp",
  industry: "Câu chuyện ngành", fomo: "Sợ bỏ lỡ" };
const OUTCOME = { recovered: "hồi về giá vốn", sold_at_loss: "bán lỗ", holding: "vẫn đang giữ" };
const NOT_ENOUGH = "chưa đủ dữ liệu để kết luận";

export function horizonText(h: Horizon): string {
  if (h.status === "not_yet") return `chưa tới (${day(h.on)})`;
  if (h.status === "missing" || h.change === null) return "thiếu giá";
  return `${pct(h.change)} (VN-Index${h.index === null ? ": thiếu số" : ` ${pct(h.index)}`})`;
}

function GroupRows({ title, rows, label }: { title: string; rows: Group[]; label: (k: string) => string }) {
  return <>{rows.map((g) => <tr key={`${title}-${g.key}`}><td>{title}: {label(g.key)}</td><td className="num">{g.count}</td>
    <td>{g.enough && g.mean ? `${pct(g.mean)} sau 6 tháng${g.mean_diff ? `, so với VN-Index ${pct(g.mean_diff)}` : ""}` : NOT_ENOUGH}</td></tr>)}</>;
}

/** Hậu kiểm quyết định: past buys, sells and holds measured on what happened afterwards. */
export function HindsightView() {
  const [data, setData] = useState<Data | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  useEffect(() => { api<Data>("hindsight").then(setData, (e) => setMessage(e instanceof ApiError ? e.failure.message : "Lỗi tải hậu kiểm.")); }, []);
  const d = data?.biases.disposition;
  return (
    <section className="surface" aria-label="Hậu kiểm quyết định">
      <h2>Hậu kiểm quyết định</h2>
      <p className="caption">Mỗi quyết định trong sổ, đo bằng điều đã xảy ra sau đó (giá đóng cửa đã lưu, chưa tính phí và thuế), so với VN-Index cùng khoảng.
        Nhóm dưới 5 lần quan sát không kết luận. Tính trên máy này, không gửi đi đâu. Không phải khuyến nghị.</p>
      {message && <p className="errors" role="alert">{message}</p>}
      {!data && !message && <p className="muted fx-loading" role="status">Đang tính hậu kiểm…</p>}
      {data && d && <>
        <h3>Thói quen</h3>
        <div className="tablewrap"><table aria-label="Thói quen">
          <thead><tr><th>Nhóm</th><th className="num">Số lần</th><th>Kết quả</th></tr></thead>
          <tbody>
            <tr><td>Bán lời sớm, giữ lỗ lâu (theo Odean)</td><td className="num">{d.days} ngày bán</td>
              <td>{d.enough && d.pgr !== null && d.plr !== null
                ? `Tỷ lệ chốt khi đang lãi ${pct(d.pgr)}, khi đang lỗ ${pct(d.plr)}${Number(d.pgr) > Number(d.plr) ? " — bạn chốt lãi nhanh hơn chốt lỗ" : ""}`
                : NOT_ENOUGH}</td></tr>
            <GroupRows title="Cảm xúc khi mua" rows={data.biases.by_emotion} label={(k) => EMOTION[k] ?? k} />
            <GroupRows title="Lý do mua" rows={data.biases.by_reason} label={(k) => REASON[k] ?? k} />
            <GroupRows title="Mua sau khi tăng hơn 15% trong 20 phiên" rows={[data.biases.chasing.chasing]} label={() => "mua đuổi"} />
            <GroupRows title="Các lần mua khác" rows={[data.biases.chasing.other]} label={() => "còn lại"} />
          </tbody>
        </table></div>

        <h3>Luận điểm bị phá</h3>
        {data.breaks.length === 0 ? <p className="muted">Chưa có điều kiện nào bị phá.</p> : <div className="tablewrap"><table aria-label="Luận điểm bị phá">
          <thead><tr><th>Mã</th><th>Bị phá</th><th>Đã giữ tiếp</th><th>Sau đó</th><th className="num">So với bán ngay</th></tr></thead>
          <tbody>{data.breaks.map((b, i) => <tr key={`${b.symbol}-${b.broken_on}-${i}`}><td>{b.symbol}</td>
            <td>{day(b.broken_on)} ở {formatDecimal(String(Number(b.broken_price) / 1000), 2)}</td><td>{b.held_on ? "có lý do" : "không"}</td>
            <td>{b.then === null ? "thiếu giá" : `${b.how === "sold" ? "bán" : "giá"} ${formatDecimal(String(Number(b.then) / 1000), 2)} (${day(b.then_on ?? "")})`}</td>
            <td className="num">{b.change === null ? "—" : pct(b.change)}</td></tr>)}</tbody>
        </table></div>}

        <h3>Giữ khi đang lỗ quá {pct(String(-Number(data.threshold)))} so với giá vốn</h3>
        <p className="caption">Dùng ngưỡng Kế hoạch sụt giảm hiện tại cho mọi khoảng trong quá khứ.</p>
        {data.loss_holds.length === 0 ? <p className="muted">Chưa có lần nào.</p> : <div className="tablewrap"><table aria-label="Giữ khi đang lỗ">
          <thead><tr><th>Mã</th><th>Từ</th><th>Đến</th><th className="num">Sâu nhất</th><th>Kết thúc</th></tr></thead>
          <tbody>{data.loss_holds.map((h) => <tr key={`${h.symbol}-${h.start}`}><td>{h.symbol}</td><td>{day(h.start)}</td>
            <td>{h.end ? `${day(h.end)} (${h.days} ngày)` : "—"}</td><td className="num">{pct(h.deepest)}</td><td>{OUTCOME[h.outcome]}</td></tr>)}</tbody>
        </table></div>}

        <h3>Từng lệnh</h3>
        {data.opening_skipped > 0 && <p className="caption">{data.opening_skipped} vị thế số dư đầu kỳ không có ngày mua nên không hậu kiểm.</p>}
        {data.trades.length === 0 ? <p className="muted">Chưa có lệnh mua bán trong sổ.</p> : <div className="tablewrap"><table aria-label="Từng lệnh">
          <thead><tr><th>Ngày</th><th>Lệnh</th><th className="num">Giá</th><th>Sau 3 tháng</th><th>Sau 6 tháng</th><th>Sau 12 tháng</th></tr></thead>
          <tbody>{data.trades.map((t) => <tr key={t.event_id}><td>{day(t.date)}</td><td>{t.type === "buy" ? "Mua" : "Bán"} {t.symbol}</td>
            <td className="num">{formatDecimal(String(Number(t.price) / 1000), 2)}</td>
            {["3", "6", "12"].map((m) => <td key={m}>{horizonText(t.horizons[m])}</td>)}</tr>)}</tbody>
        </table></div>}
        <p className="caption">Lệnh bán: số sau đó là giá đi tiếp sau khi bán (dương là bán non, âm là thoát đúng lúc). Giá tính bằng nghìn đồng.</p>
      </>}
    </section>
  );
}
