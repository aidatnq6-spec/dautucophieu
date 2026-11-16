"use client";
import { useEffect, useState } from "react";
import { ApiError, api, requestId } from "../lib/api";

type Data = { points: { date: string; value: string }[]; threshold: string | null; version: number };

/** The y range: the lowest and highest of the values and the threshold, one point of room each side. */
export function yRange(values: number[], threshold: number | null): [number, number] {
  const all = threshold === null ? values : [...values, threshold];
  return [Math.floor(Math.min(...all)) - 1, Math.ceil(Math.max(...all)) + 1];
}

/** SVG path of the values across the width (one alone sits in the middle), the range's top at y = 0. */
export function linePath(values: number[], [lo, hi]: [number, number], width: number, height: number): string {
  const x = (i: number) => (values.length === 1 ? width / 2 : (i * width) / (values.length - 1));
  const y = (v: number) => height - ((v - lo) / (hi - lo)) * height;
  return values.map((v, i) => `${i ? "L" : "M"}${Math.round(x(i) * 100) / 100},${Math.round(y(v) * 100) / 100}`).join(" ");
}

const W = 600, H = 160;
const vn = (v: number | string, d = 2) => Number(v).toLocaleString("vi-VN", { maximumFractionDigits: d });
const dmy = (iso: string) => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;

/** Chênh lệch vàng SJC so với thế giới: the kept daily gap, the owner's threshold and the Telegram note when it is crossed. */
export function SjcGap() {
  const [d, setD] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    api<Data>("macro/sjc-gap").then((x) => { setD(x); setDraft(x.threshold ? x.threshold.replace(".", ",") : ""); },
      (e) => setError(e instanceof ApiError ? e.failure.message : "Lỗi tải."));
  }, []);
  const save = async () => {
    if (!d) return;
    setBusy(true); setError(null);
    try {
      const x = await api<Data>("macro/sjc-gap", { method: "PUT", body: { threshold: draft.trim() || null, expected_version: d.version, request_id: requestId() } });
      setD(x); setDraft(x.threshold ? x.threshold.replace(".", ",") : "");
    } catch (e) { setError(e instanceof ApiError ? e.failure.message : "Không lưu được."); } finally { setBusy(false); }
  };
  const values = d?.points.map((p) => Number(p.value)) ?? [];
  const threshold = d?.threshold ? Number(d.threshold) : null;
  const range = values.length ? yRange(values, threshold) : null;
  const ty = range && threshold !== null ? H - ((threshold - range[0]) / (range[1] - range[0])) * H : null;
  const last = d?.points.at(-1);
  return (
    <section className="surface" aria-label="Chênh lệch vàng SJC so với thế giới">
      <h2>Chênh lệch vàng SJC so với thế giới</h2>
      <p className="caption">Giá bán vàng miếng SJC (Phú Quý) so với giá vàng thế giới quy ra đồng/chỉ theo tỷ giá bán Vietcombank, chưa tính thuế phí;
        mỗi ngày giữ số cuối của lượt cập nhật vĩ mô. Đặt ngưỡng để được nhắc qua Telegram khi chênh lệch vượt lên và khi xuống lại.</p>
      {error && <p className="errors" role="alert">{error}</p>}
      {!d && !error && <p className="muted fx-loading" role="status">Đang tải…</p>}
      {d && <>
        {last ? <p>Mới nhất: <strong>{vn(last.value)}%</strong> <span className="caption">ngày {dmy(last.date)}, {d.points.length} ngày đã lưu</span></p>
          : <p className="muted">Chưa có số: lượt cập nhật vĩ mô tiếp theo sẽ tính.</p>}
        {range && <svg viewBox={`0 0 ${W} ${H}`} className="sg-chart" role="img" aria-label={`Chênh lệch từ ${vn(values[0])}% đến ${vn(values.at(-1)!)}%`}>
          {ty !== null && <line x1={0} x2={W} y1={ty} y2={ty} className="sg-threshold" />}
          <path d={linePath(values, range, W, H)} className="sg-line" />
          {values.length === 1 && <circle cx={W / 2} cy={Number(linePath(values, range, W, H).split(",")[1])} r={4} className="sg-dot" />}
          <text x={4} y={12} className="sg-axis">{range[1]}%</text><text x={4} y={H - 4} className="sg-axis">{range[0]}%</text>
        </svg>}
        <form className="formgrid" aria-label="Ngưỡng nhắc chênh lệch vàng" onSubmit={(e) => { e.preventDefault(); void save(); }}>
          <label className="field">Nhắc khi chênh lệch từ (%)<input aria-label="Ngưỡng chênh lệch vàng" inputMode="decimal" placeholder="ví dụ 12"
            value={draft} onChange={(e) => setDraft(e.target.value)} /></label>
          <button type="submit" className="btn" disabled={busy}>{draft.trim() ? "Lưu ngưỡng" : "Tắt nhắc"}</button>
          <span className="caption">{threshold !== null ? `Đang nhắc khi từ ${vn(threshold)}% trở lên.` : "Chưa đặt ngưỡng: không nhắc."}</span>
        </form>
      </>}
    </section>
  );
}
