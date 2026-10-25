"use client";
import Link from "next/link";
import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { formatVnd } from "../lib/format";
import { ACTION_LABEL, REASON_TEXT, label } from "./labels";

export type Item = { entity_id: string; action: string; reasons: string[]; amount: string; quantity_requires_confirmation: boolean;
  zone: { buy_below: string; fair_value: string; margin_of_safety: string; position: string } | null; source_ids: string[];
  assumption_version: number | null; invalidate_conditions: string[]; price_date: string | null; analysis_time: string;
  suggested_shares?: number | null; lot_kind?: "round" | "odd" | null };
export type Decision = { action: string; headline: string; reasons: string[] };

function ItemDetail({ item }: { item: Item }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="surface" style={{ marginBottom: 12 }}>
      <div className="row">
        <div><span className="pill">{label(ACTION_LABEL, item.action)}</span> <strong>{item.entity_id}</strong></div>
        <button className="btn text" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
          {open ? <ChevronUp size={16} aria-hidden="true" /> : <ChevronDown size={16} aria-hidden="true" />}Xem căn cứ {item.entity_id}</button>
      </div>
      {open && (
        <div data-testid={`reasons-${item.entity_id}`}>
          <ul>{item.reasons.map((r) => <li key={r}>{label(REASON_TEXT, r)}</li>)}</ul>
          {item.zone && <p>Vùng mua ≤ {formatVnd(item.zone.buy_below)} · giá trị cơ sở {formatVnd(item.zone.fair_value)}</p>}
          {item.action === "buy_tranche" && <p>Số tiền đề xuất: {formatVnd(item.amount)}
            {item.suggested_shares ? ` · gợi ý ${item.suggested_shares.toLocaleString("vi-VN")} cổ phiếu (${item.lot_kind === "odd" ? "lô lẻ" : "lô chẵn"})` : ""}
            {" "}· hãy xác nhận số lượng và tiền khả dụng với công ty chứng khoán trước khi đặt lệnh.</p>}
          <p className="caption">Giả định định giá: {item.assumption_version ? `phiên bản ${item.assumption_version}` : "chưa có"} ·
            Ngày giá: {item.price_date ?? "chưa có"} · Phân tích lúc {new Date(item.analysis_time).toLocaleString("vi-VN")}</p>
          {item.source_ids.length > 0 && (
            <p>Nguồn: {item.source_ids.map((s) => <Link key={s} href={`/research/${item.entity_id}#${s}`}>{s} </Link>)}</p>
          )}
          {item.invalidate_conditions.length > 0 && <p className="caption">Đánh giá lại khi: {item.invalidate_conditions.join("; ")}</p>}
        </div>
      )}
    </div>
  );
}

export function DecisionSummary({ decision, items }: { decision: Decision; items: Item[] }) {
  return (
    <section className="surface" aria-labelledby="decision-title" style={{ background: "#163b55", color: "#fff", border: 0 }}>
      <span className="pill good">{label(ACTION_LABEL, decision.action)}</span>
      <h2 id="decision-title" style={{ fontSize: 24, margin: "12px 0" }}>{decision.headline}</h2>
      <ul>{decision.reasons.map((r) => <li key={r}>{label(REASON_TEXT, r)}</li>)}</ul>
      <div style={{ color: "var(--ink)" }}>{items.map((i) => <ItemDetail key={i.entity_id} item={i} />)}</div>
      <p className="caption" style={{ color: "#c7d8e5" }}>Khuyến nghị không tự tạo giao dịch; mọi lệnh do bạn tự đặt và ghi vào sổ.</p>
    </section>
  );
}
