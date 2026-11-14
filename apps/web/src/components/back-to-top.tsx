"use client";
import { useEffect, useState } from "react";
import { ArrowDown, ArrowUp } from "lucide-react";

const SHOW_AFTER = 300;  // px: early enough that every tab which scrolls at all gets the button

/** Appears once the page has scrolled a little; scrolls back smoothly (instantly when reduced motion is preferred). */
export function BackToTop() {
  const [shown, setShown] = useState(false);
  useEffect(() => {
    const update = () => setShown(window.scrollY > SHOW_AFTER);
    update();
    window.addEventListener("scroll", update, { passive: true });
    return () => window.removeEventListener("scroll", update);
  }, []);
  if (!shown) return null;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  return (
    <button type="button" className="to-top" aria-label="Lên đầu trang" title="Lên đầu trang"
      onClick={() => window.scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" })}>
      <ArrowUp size={20} aria-hidden="true" />
    </button>
  );
}

const HIDE_NEAR_BOTTOM = 300;  // px from the end: the button goes once there is little left to scroll

/** Top right: jumps to the end of a long page; shown while more than a screen's worth of page is left below. Pages load their parts
 * after the first paint, so the height is watched as well as the scroll. */
/** Scrolls to the end, and again if the page grew while it scrolled (parts that load late), until it is there or two seconds pass. */
function toEnd(reduce: boolean) {
  const started = Date.now();
  let last = -1, still = 0;
  window.scrollTo({ top: document.documentElement.scrollHeight, behavior: reduce ? "auto" : "smooth" });
  const check = () => {
    const left = document.documentElement.scrollHeight - (window.scrollY + window.innerHeight);
    if (left <= 2 || Date.now() - started > 2000) return;
    still = window.scrollY === last ? still + 1 : 0;
    last = window.scrollY;
    if (still >= 3) { window.scrollTo({ top: document.documentElement.scrollHeight, behavior: "auto" }); still = 0; }
    requestAnimationFrame(check);
  };
  requestAnimationFrame(check);
}

export function ToBottom() {
  const [shown, setShown] = useState(false);
  useEffect(() => {
    const update = () => {
      const left = document.documentElement.scrollHeight - (window.scrollY + window.innerHeight);
      setShown(left > HIDE_NEAR_BOTTOM);
    };
    update();
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    const watch = new ResizeObserver(update);
    watch.observe(document.body);
    return () => { window.removeEventListener("scroll", update); window.removeEventListener("resize", update); watch.disconnect(); };
  }, []);
  if (!shown) return null;
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  return (
    <button type="button" className="to-bottom" aria-label="Xuống cuối trang" title="Xuống cuối trang"
      onClick={() => toEnd(reduce)}>
      <ArrowDown size={20} aria-hidden="true" />
    </button>
  );
}
