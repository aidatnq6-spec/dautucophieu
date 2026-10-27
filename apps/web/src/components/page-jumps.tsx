"use client";
import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";

const MIN_SECTIONS = 3;

function headings(main: HTMLElement): HTMLHeadingElement[] {
  return Array.from(main.querySelectorAll<HTMLHeadingElement>("h2")).filter((h) => !h.closest(".page-jumps") && h.textContent?.trim());
}

/**
 * Shortcuts to the sections of the current page, read from its h2 headings (sections load at different times, so the list
 * follows the page as it fills in). Shown only on pages with at least three sections.
 */
export function PageJumps() {
  const path = usePathname();
  const [titles, setTitles] = useState<string[]>([]);
  const ref = useRef<HTMLElement | null>(null);
  useEffect(() => {
    const main = document.getElementById("main");
    if (!main) return;
    let timer: number | undefined;
    const scan = () => {
      const next = headings(main).map((h) => h.textContent!.trim());
      setTitles((prev) => (prev.length === next.length && prev.every((t, i) => t === next[i]) ? prev : next));
    };
    scan();
    const observer = new MutationObserver((records) => {
      if (records.every((r) => ref.current?.contains(r.target))) return;  // our own strip changing is not a page change
      window.clearTimeout(timer);
      timer = window.setTimeout(scan, 150);
    });
    observer.observe(main, { childList: true, subtree: true, characterData: true });
    return () => { observer.disconnect(); window.clearTimeout(timer); };
  }, [path]);
  if (titles.length < MIN_SECTIONS) return null;
  function go(index: number) {
    const main = document.getElementById("main");
    const target = main ? headings(main)[index] : undefined;
    if (!target) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    target.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  }
  return (
    <nav className="page-jumps" aria-label="Trên trang này" ref={ref}>
      {titles.map((t, i) => <button key={`${i}-${t}`} type="button" onClick={() => go(i)}>{t}</button>)}
    </nav>
  );
}
