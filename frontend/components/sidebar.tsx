"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, LayoutDashboard, FileText, Search } from "lucide-react";
import ThemeToggle from "@/components/ui/theme-toggle";

const nav = [
  { href: "/predict", label: "Predict", icon: Search },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/", label: "Reports", icon: FileText }
];

export default function Sidebar() {
  const path = usePathname();

  return (
    <aside className="hidden w-72 shrink-0 border-r bg-card/80 px-4 py-6 md:block">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground shadow-sm">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <path d="M12 2v20" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M4 7h16" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div className="text-lg font-semibold">PharmaLens</div>
        </div>
        <div className="md:hidden">
          <ThemeToggle />
        </div>
      </div>

      <nav className="mt-8 flex flex-col gap-1">
        {nav.map((item) => {
          const active = path === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                active ? "bg-primary text-primary-foreground shadow-sm" : "hover:bg-muted"
              }`}
            >
              <Icon className={`h-4 w-4 ${active ? "text-primary-foreground" : "text-muted-foreground"}`} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="mt-6 border-t pt-4">
        <div className="text-xs text-muted-foreground">Theme</div>
        <div className="mt-2">
          <ThemeToggle />
        </div>
      </div>
    </aside>
  );
}
