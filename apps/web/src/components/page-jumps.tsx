"use client";
import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";

const MIN_SECTIONS = 3;

function headings(main: HTMLElement): HTMLHeadingElement[] {
  return Array.from(main.querySelectorAll<HTMLHeadingElement>("h2")).filter((h) => !h.closest(".page-jumps") && h.textContent?.trim() && h.offsetParent !== null);  // not the parts of a page that are hidden
}

/**
 * Shortcuts to the sections of the current page, read from its h2 headings (sections load at different times, so the list
 * follows the page as it fills in). Shown only on pages with at least three sections.
 */
export function PageJumps() {
  const path = usePathname();
  const [titles, setTitles] = useState<string[]>([]);
  const [current, setCurrent] = useState(-1);
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
    observer.observe(main, { childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ["hidden"] });
    return () => { observer.disconnect(); window.clearTimeout(timer); };
  }, [path]);
  useEffect(() => {  // the section being read: the last heading that has reached the top of the window (below the strip)
    const main = document.getElementById("main");
    if (!main || titles.length < MIN_SECTIONS) return;
    let frame = 0;
    const update = () => {
      frame = 0;
      const line = (ref.current?.getBoundingClientRect().bottom ?? 0) + 24;
      const list = headings(main);
      let at = -1;
      list.forEach((h, i) => { if (h.getBoundingClientRect().top <= line) at = i; });
      setCurrent(at);
      const button = at >= 0 ? ref.current?.querySelectorAll("button")[at] : undefined;
      const strip = ref.current;
      if (button && strip && strip.scrollWidth > strip.clientWidth) {  // keep the highlighted shortcut in view on a long strip
        const left = button.offsetLeft - strip.offsetLeft;
        if (left < strip.scrollLeft || left + button.offsetWidth > strip.scrollLeft + strip.clientWidth) strip.scrollLeft = left - 16;
      }
    };
    const onScroll = () => { if (!frame) frame = window.requestAnimationFrame(update); };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => { window.removeEventListener("scroll", onScroll); if (frame) window.cancelAnimationFrame(frame); };
  }, [titles]);
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
      {titles.map((t, i) => <button key={`${i}-${t}`} type="button" aria-current={i === current ? "true" : undefined} onClick={() => go(i)}>{t}</button>)}
    </nav>
  );
}
