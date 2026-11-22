"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, BookOpenText, Building2, CalendarCheck, ClipboardList, Briefcase, CalendarDays, ChartLine, Eye, FlaskConical, Grid3x3, Globe, House, Newspaper, NotebookPen, PiggyBank, Scale, Settings, UserRound, Workflow } from "lucide-react";

// Six short groups, each with its own accent colour (nav-tone-*), so the eye finds where a group starts.
const GROUPS = [
  { title: null, tone: null, links: [{ href: "/", label: "Tổng quan", icon: House }] },
  { title: "Tài sản", tone: "assets", links: [
    { href: "/portfolio", label: "Danh mục & Giao dịch", icon: Briefcase },
    { href: "/profile", label: "Hồ sơ & rủi ro", icon: UserRound },
    { href: "/year", label: "Năm tài chính", icon: CalendarCheck }] },
  { title: "Vĩ mô & thị trường", tone: "market", links: [
    { href: "/macro", label: "Vĩ mô", icon: Globe },
    { href: "/market", label: "Thị trường trong phiên", icon: ChartLine },
    { href: "/trend", label: "Xu hướng", icon: Activity },
    { href: "/history", label: "Thống kê lịch sử", icon: FlaskConical }] },
  { title: "Phân tích ngành", tone: "sectors", links: [
    { href: "/value-chains", label: "Chuỗi giá trị", icon: Workflow },
    { href: "/sectors", label: "Ngành theo quý", icon: Grid3x3 }] },
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
    { href: "/loan", label: "Vay & bất động sản", icon: Building2 },
    { href: "/journal", label: "Nhật ký", icon: NotebookPen },
    { href: "/settings", label: "Cài đặt", icon: Settings }] },
];

/** The menu's name of a page path ("/macro" is "Vĩ mô"); pages outside the menu keep their path. */
export function pageLabel(page: string): string {
  return GROUPS.flatMap((g) => g.links).find((l) => l.href === page)?.label ?? page;
}

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
