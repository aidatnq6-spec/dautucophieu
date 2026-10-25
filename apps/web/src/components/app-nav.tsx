"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpenText, Briefcase, Eye, House, Search, Settings, UserRound } from "lucide-react";

const LINKS = [
  { href: "/", label: "Tổng quan", icon: House },
  { href: "/portfolio", label: "Danh mục & giao dịch", icon: Briefcase },
  { href: "/watchlist", label: "Theo dõi", icon: Eye },
  { href: "/research", label: "Nghiên cứu", icon: Search },
  { href: "/reports", label: "Bản tin sau phiên", icon: BookOpenText },
  { href: "/profile", label: "Hồ sơ & rủi ro", icon: UserRound },
  { href: "/settings", label: "Cài đặt", icon: Settings },
];

export function AppNav() {
  const path = usePathname();
  return (
    <nav className="nav" aria-label="Điều hướng chính">
      {LINKS.map(({ href, label, icon: Icon }) => (
        <Link key={href} href={href} aria-current={path === href ? "page" : undefined}>
          <Icon size={18} aria-hidden="true" />{label}
        </Link>
      ))}
    </nav>
  );
}
