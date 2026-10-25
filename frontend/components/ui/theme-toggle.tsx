"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function ThemeToggle() {
  const [isDark, setIsDark] = useState<boolean>(false);
  const [mounted, setMounted] = useState(false);

  // Read persisted preference only on mount to avoid SSR/client hydration mismatch
  useEffect(() => {
    setMounted(true);
    try {
      const saved = localStorage.getItem("pharmalens:theme");
      if (saved) {
        setIsDark(saved === "dark");
        return;
      }
      const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
      setIsDark(Boolean(prefersDark));
    } catch (e) {
      // ignore and stay with default
    }
  }, []);

  useEffect(() => {
    if (!mounted) return;
    const root = document.documentElement;
    if (isDark) {
      root.classList.add("dark");
      localStorage.setItem("pharmalens:theme", "dark");
    } else {
      root.classList.remove("dark");
      localStorage.setItem("pharmalens:theme", "light");
    }
  }, [isDark, mounted]);

  return (
    <Button variant="ghost" size="icon" aria-label="Toggle theme" onClick={() => setIsDark((v) => !v)}>
      {mounted ? (isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />) : <span className="h-4 w-4" />}
    </Button>
  );
}
