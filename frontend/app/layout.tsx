import type { Metadata } from "next";
import Link from "next/link";
import { Activity, BarChart3, Search } from "lucide-react";
import ThemeToggle from "@/components/ui/theme-toggle";
import Header from "@/components/header";
import Sidebar from "@/components/sidebar";

import "./globals.css";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "PharmaLens",
  description: "Drug side-effect risk prediction system"
};

const navItems = [
  { href: "/predict", label: "Predict", icon: Search },
  { href: "/dashboard", label: "Dashboard", icon: BarChart3 }
];

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen">
          <a href="#content" className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:bg-card focus:p-2 focus:rounded-md">
            Skip to content
          </a>
          <Header />
          <div className="mx-auto flex max-w-7xl gap-6 px-4 py-8 lg:px-8">
            <Sidebar />
            <div className="flex min-w-0 flex-1 flex-col">{children}</div>
          </div>
        </div>
      </body>
    </html>
  );
}

