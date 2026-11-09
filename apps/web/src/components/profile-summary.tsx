"use client";
import Link from "next/link";
import { type KeyboardEvent, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ApiError, api } from "../lib/api";
import { PropertyBook } from "./property-book";
import { CycleTargets } from "./cycle-targets";
import { NewMoney } from "./new-money";
import { DepositBook } from "./deposit-book";
import { EquityBudget } from "./equity-budget";
import { WealthCheck } from "./wealth-check";
import { LifestyleInflation } from "./lifestyle";
import { Intangibles } from "./intangibles";
import { Contributions } from "./contributions";
import { Accumulation } from "./accumulation";
import { MoneyPurposes } from "./money-purposes";
import { PassiveIncome } from "./passive-income";
import { type Assessment } from "./profile-form";
import { RiskSection } from "./risk-section";

type ProfileView = { version: number; assessment: Assessment; confirmed_at: string; freshness: { status: string; allows_new_recommendations: boolean } };
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

const TABS = [["rui-ro", "Rủi ro"], ["tai-san", "Tài sản"], ["dong-tien", "Dòng tiền & mục tiêu"], ["ke-hoach", "Kế hoạch"]] as const;

/** Hồ sơ & rủi ro in four parts, one shown at a time. All stay mounted, so what is being typed in a part survives leaving it; the open part is in the address. */
export function ProfileSummary() {
  const asked = useSearchParams().get("tab");
  const tab = TABS.find(([id]) => id === asked)?.[0] ?? TABS[0][0];
  const open = (id: string) => window.history.replaceState(null, "", `/profile?tab=${id}`);
  function onTabKey(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    e.preventDefault();
    const next = TABS[(TABS.findIndex(([id]) => id === tab) + (e.key === "ArrowRight" ? 1 : TABS.length - 1)) % TABS.length][0];
    open(next);
    document.getElementById(`tab-${next}`)?.focus();
  }
  const profile = useRecord<ProfileView>("profile");
  const [riskChanges, setRiskChanges] = useState(0);
  const [wealthSaves, setWealthSaves] = useState(0);
  const [intangibleChanges, setIntangibleChanges] = useState(0);
  const [bookSaves, setBookSaves] = useState(0);
  const [bookPosts, setBookPosts] = useState(0);
  const [propertySaves, setPropertySaves] = useState(0);
  if (profile.error) return <p className="errors" role="alert">{profile.error}</p>;
  if (profile.value === undefined) return <p className="muted fx-loading" role="status">Đang tải…</p>;
  const p = profile.value;
  return (
    <>
      <div className="tabs" role="tablist" aria-label="Các phần của hồ sơ" onKeyDown={onTabKey}>
        {TABS.map(([id, label]) => <button key={id} type="button" role="tab" id={`tab-${id}`} aria-controls={`panel-${id}`} aria-selected={tab === id} tabIndex={tab === id ? 0 : -1} onClick={() => open(id)}>{label}</button>)}
      </div>
      <div role="tabpanel" id="panel-rui-ro" aria-labelledby="tab-rui-ro" hidden={tab !== "rui-ro"}>
        {/* The confirmed profile still gates new recommendations; it needs the owner only when missing or due, so it is shown only then. */}
        {(!p || p.freshness.status !== "current") && <section className="surface" aria-label="Vốn có thể đầu tư">
          <div className="row"><h2>Hồ sơ tài chính</h2><Link href="/onboarding">Cập nhật hồ sơ</Link></div>
          {!p ? <p className="notice">Chưa có hồ sơ tài chính đã xác nhận.</p>
            : <p className="notice">{FRESHNESS[p.freshness.status]} (xác nhận {new Date(p.confirmed_at).toLocaleDateString("vi-VN")}).
              {!p.freshness.allows_new_recommendations && " Gợi ý mua mới tạm dừng cho tới khi bạn xác nhận lại."}</p>}
        </section>}
        <RiskSection onChanged={() => setRiskChanges((n) => n + 1)} />
      </div>
      <div role="tabpanel" id="panel-tai-san" aria-labelledby="tab-tai-san" hidden={tab !== "tai-san"}>
        <DepositBook refresh={bookPosts} onSaved={() => setBookSaves((n) => n + 1)} />
        <MoneyPurposes refresh={bookSaves} />
        <PropertyBook refresh={`${riskChanges}-${bookSaves}`} onSaved={() => setPropertySaves((n) => n + 1)} />
        <EquityBudget refresh={`${riskChanges}-${intangibleChanges}-${bookSaves}`} />
        <Intangibles onChanged={() => setIntangibleChanges((n) => n + 1)} />
      </div>
      <div role="tabpanel" id="panel-dong-tien" aria-labelledby="tab-dong-tien" hidden={tab !== "dong-tien"}>
        <WealthCheck onSaved={() => setWealthSaves((n) => n + 1)} />
        <LifestyleInflation refresh={wealthSaves} />
        <PassiveIncome refresh={`${riskChanges}-${bookSaves}-${wealthSaves}-${propertySaves}`} />
      </div>
      <div role="tabpanel" id="panel-ke-hoach" aria-labelledby="tab-ke-hoach" hidden={tab !== "ke-hoach"}>
        <Contributions />
        <Accumulation onPosted={() => { setBookPosts((n) => n + 1); setBookSaves((n) => n + 1); }} />
        <NewMoney />
        <CycleTargets refresh={`${riskChanges}-${bookSaves}`} />
      </div>
    </>
  );
}
