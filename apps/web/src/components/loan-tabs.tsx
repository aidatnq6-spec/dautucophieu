"use client";
import type { KeyboardEvent } from "react";
import { useSearchParams } from "next/navigation";
import { BuildingTool } from "./building-tool";
import { LoanTool } from "./loan-tool";
import { RentalCompare } from "./rental-compare";

export const TABS = [["khoan-vay", "Khoản vay"], ["mua-nha-cho-thue", "Mua nhà cho thuê"], ["toa-nha", "Tòa nhà cho thuê"]] as const;

/** Vay & bất động sản in three parts, one shown at a time. All stay mounted, so what is typed in a part survives leaving it; the open part is in the address. */
export function LoanTabs() {
  const params = useSearchParams();
  const asked = params.get("tab");
  const tab = TABS.find(([id]) => id === asked)?.[0] ?? TABS[0][0];
  const open = (id: string) => {
    const next = new URLSearchParams(params.toString());
    next.set("tab", id);
    window.history.replaceState(null, "", `/loan?${next.toString()}`);
  };
  function onTabKey(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    e.preventDefault();
    const next = TABS[(TABS.findIndex(([id]) => id === tab) + (e.key === "ArrowRight" ? 1 : TABS.length - 1)) % TABS.length][0];
    open(next);
    document.getElementById(`tab-${next}`)?.focus();
  }
  return (
    <>
      <div className="tabs" role="tablist" aria-label="Các phần của Vay & bất động sản" onKeyDown={onTabKey}>
        {TABS.map(([id, label]) => <button key={id} type="button" role="tab" id={`tab-${id}`} aria-controls={`panel-${id}`} aria-selected={tab === id}
          tabIndex={tab === id ? 0 : -1} onClick={() => open(id)}>{label}</button>)}
      </div>
      <div role="tabpanel" id="panel-khoan-vay" aria-labelledby="tab-khoan-vay" hidden={tab !== "khoan-vay"}><LoanTool /></div>
      <div role="tabpanel" id="panel-mua-nha-cho-thue" aria-labelledby="tab-mua-nha-cho-thue" hidden={tab !== "mua-nha-cho-thue"}><RentalCompare /></div>
      <div role="tabpanel" id="panel-toa-nha" aria-labelledby="tab-toa-nha" hidden={tab !== "toa-nha"}><BuildingTool /></div>
    </>
  );
}
