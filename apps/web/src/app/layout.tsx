import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { THEME_SCRIPT } from "../lib/theme-script";

export const metadata: Metadata = { title: "Quản lý Gia Sản" };
export default function RootLayout({ children }: { children: ReactNode }) {
  return <html lang="vi" suppressHydrationWarning><head><script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} /></head><body>{children}</body></html>;
}
