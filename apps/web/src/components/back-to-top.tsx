"use client";
import { useEffect, useState } from "react";
import { ArrowUp } from "lucide-react";

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
