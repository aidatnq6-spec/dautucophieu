"use client";
import { useCallback, useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatVnd } from "../lib/format";
import { SourceEvidence, type Evidence } from "./source-evidence";
import { ValuationReview, type ValuationView } from "./valuation-review";

type Research = { entity_id: string; provenance: string; industry: string | null; in_universe: boolean;
  price: { price: string; session_date: string } | null; evidence: Evidence[]; valuation: ValuationView | null };

export function ResearchEntity({ entityId }: { entityId: string }) {
  const [data, setData] = useState<Research | null>(null);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(() => api<Research>(`research/${encodeURIComponent(entityId)}`)
    .then(setData, (e) => setError(e instanceof ApiError ? e.failure.message : "Không tải được dữ liệu.")), [entityId]);
  useEffect(() => { void load(); }, [load]);
  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!data) return <p className="muted">Đang tải…</p>;
  return (
    <>
      <div className="pagehead"><h1>{data.entity_id}</h1>
        <p className="muted">{data.industry ?? "Chưa phân ngành"} · {data.in_universe ? "Trong danh sách nghiên cứu" : "Ngoài danh sách nghiên cứu"} ·
          Giá: {data.price ? `${formatVnd(data.price.price)} (${data.price.session_date})` : "chưa có giá đã xác minh"}</p></div>
      {data.provenance === "synthetic" && <p className="notice">Dữ liệu thị trường tổng hợp để kiểm thử.</p>}
      {data.valuation ? <ValuationReview entityId={data.entity_id} view={data.valuation} onChanged={() => void load()} />
        : <p className="notice">Chưa có giả định định giá: chưa có vùng giá hay khuyến nghị mua cho mã này.</p>}
      <SourceEvidence items={data.evidence} />
    </>
  );
}
