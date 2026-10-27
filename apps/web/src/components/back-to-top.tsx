"use client";
import { useEffect, useState } from "react";
import { ArrowUp } from "lucide-react";

/** Appears once the page has scrolled past one screen; scrolls back smoothly (instantly when reduced motion is preferred). */
export function BackToTop() {
  const [shown, setShown] = useState(false);
  useEffect(() => {
    const update = () => setShown(window.scrollY > window.innerHeight);
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
