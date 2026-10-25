"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatVnd } from "../lib/format";
import { DecisionSummary, type Decision, type Item } from "./decision-summary";
import { HoldingsTable, type HoldingRow } from "./holdings-table";
import { NOTE_TEXT } from "./labels";

type Overview = { provenance: string; as_of: string; setup: { profile: boolean; risk: boolean; universe_version: number; universe_status: string | null };
  decision: Decision; items: Item[]; holdings: HoldingRow[]; quality_notes: string[];
  capital: { investable_capital: string | null; status: string } | null; ledger: { cash: string; realized_gain: string } };

export function OverviewView() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api<Overview>("overview").then(setData, (e) => setError(e instanceof ApiError ? e.failure.message : "Không tải được tổng quan.")); }, []);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!data) return <p className="muted">Đang tải…</p>;
  return (
    <>
      {data.provenance === "synthetic" && <p className="notice"><strong>Dữ liệu thị trường tổng hợp</strong> để kiểm thử: không phải giá hay khuyến nghị thật.</p>}
      {data.provenance === "none" && <p className="notice">Chưa kết nối nguồn dữ liệu thị trường được phép dùng: chưa có giá và khuyến nghị thật.</p>}
      {(!data.setup.profile || !data.setup.risk) && <p className="notice">Chưa hoàn tất hồ sơ và khảo sát. <Link href="/onboarding">Thiết lập ngay</Link></p>}
      {data.setup.universe_status !== "complete" && <p className="caption">Danh sách 50 mã nghiên cứu chưa được duyệt đầy đủ (phiên bản {data.setup.universe_version}).</p>}
      <DecisionSummary decision={data.decision} items={data.items} />
      <section className="surface">
        <div className="row"><h2>Cổ phiếu đang nắm giữ</h2><Link href="/portfolio">Sổ giao dịch</Link></div>
        <p className="caption">Vốn có thể đầu tư: {formatVnd(data.capital?.investable_capital ?? null)} · Tiền trong sổ: {formatVnd(data.ledger.cash)}</p>
        <HoldingsTable rows={data.holdings} />
        {data.quality_notes.map((n) => <p key={n} className="caption">{NOTE_TEXT(n)}</p>)}
        <p className="caption">Chưa hiển thị tỷ suất sinh lời theo thời gian (TWR/XIRR) vì chưa kiểm chứng dòng tiền.</p>
      </section>
    </>
  );
}
