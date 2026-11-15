"use client";
import { useSearchParams } from "next/navigation";
import type { KeyboardEvent } from "react";
import { SectorsView } from "./sectors-view";
import { ValueChains } from "./value-chains";

const TABS = [["theo-quy", "Ngành theo quý"], ["chuoi-gia-tri", "Chuỗi giá trị"]] as const;

/** Phân tích ngành in two parts, one shown at a time; both stay mounted, and the open part (and the chosen sector) are in the address. */
export function SectorAnalysis() {
  const params = useSearchParams();
  const tab = TABS.find(([id]) => id === params.get("tab"))?.[0] ?? TABS[0][0];
  function open(id: string) {
    const next = new URLSearchParams(params.toString());
    next.set("tab", id);
    window.history.replaceState(null, "", `/sectors?${next.toString()}`);
  }
  function onTabKey(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
    e.preventDefault();
    const next = TABS[(TABS.findIndex(([id]) => id === tab) + (e.key === "ArrowRight" ? 1 : TABS.length - 1)) % TABS.length][0];
    open(next);
    document.getElementById(`tab-${next}`)?.focus();
  }
  return (
    <>
      <div className="tabs" role="tablist" aria-label="Các phần của phân tích ngành" onKeyDown={onTabKey}>
        {TABS.map(([id, label]) => <button key={id} type="button" role="tab" id={`tab-${id}`} aria-controls={`panel-${id}`} aria-selected={tab === id}
          tabIndex={tab === id ? 0 : -1} onClick={() => open(id)}>{label}</button>)}
      </div>
      <div role="tabpanel" id="panel-theo-quy" aria-labelledby="tab-theo-quy" hidden={tab !== "theo-quy"}>
        <p className="muted">Bản đồ nhiệt kết quả theo quý và định giá P/B của cả ngành, trên các mã trong danh sách theo dõi.</p>
        <SectorsView />
      </div>
      <div role="tabpanel" id="panel-chuoi-gia-tri" aria-labelledby="tab-chuoi-gia-tri" hidden={tab !== "chuoi-gia-tri"}>
        <ValueChains />
      </div>
    </>
  );
}
