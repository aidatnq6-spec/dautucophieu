"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, BookOpenText, ClipboardList, Briefcase, Calculator, CalendarDays, ChartLine, Eye, Grid3x3, Globe, House, Newspaper, NotebookPen, PiggyBank, Scale, Settings, UserRound } from "lucide-react";

// Five short groups, each with its own accent colour (nav-tone-*), so the eye finds where a group starts.
const GROUPS = [
  { title: null, tone: null, links: [{ href: "/", label: "Tổng quan", icon: House }] },
  { title: "Tài sản", tone: "assets", links: [
    { href: "/portfolio", label: "Danh mục & Giao dịch", icon: Briefcase },
    { href: "/profile", label: "Hồ sơ & rủi ro", icon: UserRound }] },
  { title: "Vĩ mô & thị trường", tone: "market", links: [
    { href: "/macro", label: "Vĩ mô", icon: Globe },
    { href: "/market", label: "Thị trường trong phiên", icon: ChartLine },
    { href: "/sectors", label: "Ngành theo quý", icon: Grid3x3 },
    { href: "/trend", label: "Xu hướng", icon: Activity }] },
  { title: "Cổ phiếu", tone: "stocks", links: [
    { href: "/watchlist", label: "Theo dõi", icon: Eye },
    { href: "/fair-value", label: "Định giá", icon: Scale },
    { href: "/earnings", label: "Mùa báo cáo", icon: ClipboardList },
    { href: "/events", label: "Lịch sự kiện", icon: CalendarDays },
    { href: "/funds", label: "Quỹ mở", icon: PiggyBank }] },
  { title: "Tin tức", tone: "news", links: [
    { href: "/insights", label: "Nhận định", icon: Newspaper },
    { href: "/reports", label: "Bản tin sau phiên", icon: BookOpenText }] },
  { title: "Công cụ", tone: "tools", links: [
    { href: "/loan", label: "Tính khoản vay", icon: Calculator },
    { href: "/journal", label: "Nhật ký", icon: NotebookPen },
    { href: "/settings", label: "Cài đặt", icon: Settings }] },
];

export function AppNav() {
  const path = usePathname();
  return (
    <nav className="nav" aria-label="Điều hướng chính">
      {GROUPS.map(({ title, tone, links }) => (
        <div key={title ?? "top"} className={`nav-group${tone ? ` nav-tone-${tone}` : ""}`} role="group" aria-label={title ?? "Chung"}>
          {title && <span className="nav-head">{title}</span>}
          {links.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href} aria-current={path === href ? "page" : undefined}>
              <Icon size={18} aria-hidden="true" />{label}
            </Link>
          ))}
        </div>
      ))}
    </nav>
  );
}
