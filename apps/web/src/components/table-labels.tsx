"use client";
import { useEffect } from "react";

/** The heading of every column of a table: header rows walked with their spans; a group heading joined to its column's own ("Định giá · P/E"). */
function headings(table: HTMLTableElement): string[] {
  const grid: string[][] = [];
  const rows = table.tHead ? [...table.tHead.rows] : [];
  rows.forEach((row, r) => {
    grid[r] ??= [];
    let col = 0;
    for (const cell of [...row.cells]) {
      while (grid[r][col] !== undefined) col++;
      const text = (cell.textContent ?? "").replace(/\s+/g, " ").trim();
      for (let dr = 0; dr < Math.max(1, cell.rowSpan); dr++) {
        grid[r + dr] ??= [];
        for (let dc = 0; dc < Math.max(1, cell.colSpan); dc++) grid[r + dr][col + dc] = text;
      }
      col += Math.max(1, cell.colSpan);
    }
  });
  const width = Math.max(0, ...grid.map((g) => g.length));
  return Array.from({ length: width }, (_, c) => [...new Set(grid.map((g) => g[c]).filter((t): t is string => !!t))].join(" · "));
}

/** Gives every body cell the heading of its column (kept when already set), so on a narrow screen each row reads as a card
 * ("Giá: 100"); a table without headings is left as it is. */
export function labelTable(table: HTMLTableElement): void {
  const names = headings(table);
  if (!names.some(Boolean)) return;
  for (const body of [...table.tBodies]) {
    for (const row of [...body.rows]) {
      let col = 0;
      for (const cell of [...row.cells]) {
        if (!cell.hasAttribute("data-label") && names[col]) cell.setAttribute("data-label", names[col]);
        col += Math.max(1, cell.colSpan);
      }
    }
  }
  table.setAttribute("data-cards", "1");
}

/** Labels the tables of the page as they appear, so none needs a sideways scroll on a phone. */
export function TableLabels() {
  useEffect(() => {
    let queued = 0;
    const run = () => { queued = 0; document.querySelectorAll<HTMLTableElement>("main table").forEach(labelTable); };
    const observer = new MutationObserver(() => { if (!queued) queued = window.requestAnimationFrame(run); });
    run();
    observer.observe(document.querySelector("main") ?? document.body, { childList: true, subtree: true });
    return () => { observer.disconnect(); if (queued) window.cancelAnimationFrame(queued); };
  }, []);
  return null;
}
