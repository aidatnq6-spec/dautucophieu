"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ApiError, api } from "../lib/api";
import { ProfileForm } from "./profile-form";
import { GROUP_LABEL, RiskSurvey } from "./risk-survey";

type Step = "profile" | "risk" | "ledger";
type Saved = { version: number; data: Record<string, unknown> | null };
const STEPS: [Step, string][] = [["profile", "1. Hồ sơ tài chính"], ["risk", "2. Khảo sát 13 câu"], ["ledger", "3. Sổ giao dịch"]];

async function current(path: string): Promise<Saved> {
  try {
    const data = await api<Record<string, unknown> & { version: number }>(path);
    return { version: data.version, data };
  } catch (e) {
    if (e instanceof ApiError && e.failure.status === 404) return { version: 0, data: null };
    throw e;
  }
}

export function OnboardingFlow() {
  const [step, setStep] = useState<Step>("profile");
  const [profile, setProfile] = useState<Saved | null>(null);
  const [risk, setRisk] = useState<Saved | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => Promise.all([current("profile"), current("risk")]).then(([p, r]) => { setProfile(p); setRisk(r); },
    (e) => setError(e instanceof ApiError ? e.failure.message : "Không tải được hồ sơ.")), []);
  useEffect(() => { void load(); }, [load]);

  if (error) return <p className="errors" role="alert">{error}</p>;
  if (!profile || !risk) return <p className="muted">Đang tải…</p>;
  const group = (risk.data?.assessment as { group?: string } | undefined)?.group;
  return (
    <>
      <ol className="steps">{STEPS.map(([id, label]) => <li key={id} aria-current={id === step ? "step" : undefined}>{label}</li>)}</ol>
      <p className="caption">Thông tin chỉ được lưu khi bạn bấm xác nhận; phần đang nhập dở không được ghi vào kho dữ liệu.</p>
      {step === "profile" && (
        <section className="surface">
          <h2>Hồ sơ tài chính và vốn có thể đầu tư</h2>
          {profile.data && <p className="pill good">Đã có hồ sơ xác nhận (phiên bản {profile.version}); lưu mới sẽ tạo phiên bản tiếp theo.</p>}
          <ProfileForm version={profile.version} onSaved={async () => { await load(); setStep("risk"); }} />
          {profile.data && <div className="actions"><button className="btn" onClick={() => setStep("risk")}>Giữ hồ sơ hiện tại, sang khảo sát</button></div>}
        </section>
      )}
      {step === "risk" && (
        <section className="surface">
          <h2>Khảo sát rủi ro</h2>
          {group && <p className="pill">Kết quả đã lưu: {GROUP_LABEL[group] ?? group}</p>}
          <RiskSurvey version={risk.version} onSaved={async (r) => { await load(); if (r.ready_for_allocation) setStep("ledger"); }} />
        </section>
      )}
      {step === "ledger" && (
        <section className="surface">
          <h2>Nhập số dư và giao dịch</h2>
          <p>Hồ sơ và khảo sát đã lưu. Tiếp theo, ghi nộp tiền, mua/bán hoặc số dư đầu kỳ trong sổ.</p>
          <Link className="btn primary" href="/portfolio">Mở sổ giao dịch</Link>
        </section>
      )}
    </>
  );
}
