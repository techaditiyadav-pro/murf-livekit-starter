'use client';

import Link from 'next/link';
import { Headset, LayoutDashboard, Sprout } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function NavHeader() {
  return (
    <header className="border-border/60 bg-background/85 sticky top-0 z-50 w-full border-b backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
        <Link
          href="/"
          className="text-foreground flex items-center gap-2 font-bold transition hover:opacity-90"
        >
          <div className="bg-primary text-primary-foreground flex size-9 items-center justify-center rounded-xl shadow-sm">
            <Sprout className="size-5" />
          </div>
          <div>
            <span className="text-base sm:text-lg">🌾 KrishiMitra AI</span>
            <span className="text-primary ml-2 hidden text-xs font-medium sm:inline">
              ● Farm &amp; Field Assistant
            </span>
          </div>
        </Link>

        <div className="flex items-center gap-2 sm:gap-3">
          <Link href="/help">
            <Button
              variant="default"
              size="sm"
              className="flex items-center gap-1.5 rounded-xl bg-amber-600 px-3.5 py-2 text-xs font-bold text-white shadow-sm hover:bg-amber-700 sm:text-sm"
            >
              <Headset className="size-4" />
              <span>Human Help</span>
            </Button>
          </Link>

          <Link href="/escalations">
            <Button
              variant="outline"
              size="sm"
              className="border-border flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-semibold sm:text-sm"
            >
              <LayoutDashboard className="size-4" />
              <span className="hidden sm:inline">Dashboard</span>
            </Button>
          </Link>
        </div>
      </div>
    </header>
  );
}
