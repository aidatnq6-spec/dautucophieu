"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { formatVnd } from "../lib/format";
import { BreakdownTable, STATUS_LABEL, WARNING_LABEL, type Assessment } from "./profile-form";
import { FLAG_LABEL, GROUP_LABEL, type RiskAssessment } from "./risk-survey";

type ProfileView = { version: number; assessment: Assessment; confirmed_at: string; freshness: { status: string; allows_new_recommendations: boolean } };
type RiskView = { version: number; assessment: RiskAssessment; assessed_at: string };
const FRESHNESS: Record<string, string> = { current: "Còn hiệu lực", refresh_soon: "Sắp đến hạn rà soát tháng",
  reconfirm_required: "Cần xác nhận lại trước khuyến nghị mới" };

function useRecord<T>(path: string) {
  const [value, setValue] = useState<T | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api<T>(path).then(setValue).catch((e) => {
      if (e instanceof ApiError && e.failure.status === 404) setValue(null);
      else setError(e instanceof ApiError ? e.failure.message : "Không tải được dữ liệu.");
    });
  }, [path]);
  return { value, error };
}

export function ProfileSummary() {
  const profile = useRecord<ProfileView>("profile");
  const risk = useRecord<RiskView>("risk");
  if (profile.error || risk.error) return <p className="errors" role="alert">{profile.error ?? risk.error}</p>;
  if (profile.value === undefined || risk.value === undefined) return <p className="muted fx-loading" role="status">Đang tải…</p>;
  const p = profile.value, r = risk.value;
  return (
    <>
      <section className="surface">
        <div className="row"><h2>Vốn có thể đầu tư</h2><Link href="/onboarding">Cập nhật hồ sơ</Link></div>
        {!p ? <p className="notice">Chưa có hồ sơ tài chính đã xác nhận.</p> : (<>
          <p><span className="pill">{STATUS_LABEL[p.assessment.status]}</span>{" "}
            <span className={`pill ${p.freshness.allows_new_recommendations ? "good" : "warn"}`}>{FRESHNESS[p.freshness.status]}</span></p>
          <p className="caption">Xác nhận lúc {new Date(p.confirmed_at).toLocaleString("vi-VN")} · phiên bản {p.version}</p>
          <BreakdownTable assessment={p.assessment} />
          {p.assessment.warnings.map((w) => <p key={w.code} className="notice">{WARNING_LABEL[w.code] ?? w.code}: {formatVnd(w.amount)}</p>)}
        </>)}
      </section>
      <section className="surface">
        <h2>Khảo sát rủi ro</h2>
        {!r ? <p className="notice">Chưa có kết quả khảo sát.</p> : (<>
          <p><span className="pill">{GROUP_LABEL[r.assessment.group]} · {r.assessment.total} điểm</span></p>
          <p className="caption">Khảo sát tổng hợp bản nháp, chưa được kiểm định · {r.assessment.questionnaire_version}</p>
          <ul>{r.assessment.flags.map((f) => <li key={f.code}>{FLAG_LABEL[f.code] ?? f.code}</li>)}</ul>
        </>)}
      </section>
    </>
  );
}
