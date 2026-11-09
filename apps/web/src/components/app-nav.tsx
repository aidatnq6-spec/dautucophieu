"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, BookOpenText, Briefcase, Calculator, CalendarDays, ChartLine, Eye, Globe, House, Newspaper, NotebookPen, Scale, Settings, UserRound } from "lucide-react";

const GROUPS = [
  { title: null, links: [{ href: "/", label: "Tổng quan", icon: House }] },
  { title: "Tài sản", links: [
    { href: "/portfolio", label: "Danh mục & Giao dịch", icon: Briefcase },
    { href: "/profile", label: "Hồ sơ & rủi ro", icon: UserRound }] },
  { title: "Thị trường", links: [
    { href: "/macro", label: "Vĩ mô", icon: Globe },
    { href: "/market", label: "Thị trường & Ngành", icon: ChartLine },
    { href: "/trend", label: "Xu hướng", icon: Activity },
    { href: "/watchlist", label: "Theo dõi", icon: Eye },
    { href: "/events", label: "Lịch sự kiện", icon: CalendarDays },
    { href: "/insights", label: "Nhận định", icon: Newspaper },
    { href: "/reports", label: "Bản tin sau phiên", icon: BookOpenText }] },
  { title: "Công cụ", links: [
    { href: "/fair-value", label: "Định giá", icon: Scale },
    { href: "/loan", label: "Tính khoản vay", icon: Calculator },
    { href: "/journal", label: "Nhật ký", icon: NotebookPen },
    { href: "/settings", label: "Cài đặt", icon: Settings }] },
];

export function AppNav() {
  const path = usePathname();
  return (
    <nav className="nav" aria-label="Điều hướng chính">
      {GROUPS.map(({ title, links }) => (
        <div key={title ?? "top"} className="nav-group" role="group" aria-label={title ?? "Chung"}>
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
