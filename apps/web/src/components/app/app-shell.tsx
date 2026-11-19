"use client";

import { ChevronsLeft, ChevronsRight, LogOut, Menu, Network, Settings, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, useSyncExternalStore } from "react";

import { ConceptSearch } from "@/components/app/concept-search";
import { useMe, useSignOut } from "@/components/app/me-provider";
import { ADMIN_NAV, MAIN_NAV, type NavItem } from "@/components/app/nav";
import { ThemeSync } from "@/components/app/theme-sync";
import { UsageMeter } from "@/components/app/usage-meter";
import { WakingBanner } from "@/components/app/waking-banner";
import { ErrorState } from "@/components/shared/error-state";
import { ThemeSwitcher } from "@/components/theme/theme-switcher";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

const COLLAPSE_KEY = "cognexa-sidebar-collapsed";
const collapseListeners = new Set<() => void>();
function subscribeCollapse(listener: () => void) {
  collapseListeners.add(listener);
  window.addEventListener("storage", listener);
  return () => {
    collapseListeners.delete(listener);
    window.removeEventListener("storage", listener);
  };
}
function readCollapsed(): boolean {
  try {
    return localStorage.getItem(COLLAPSE_KEY) === "1";
  } catch {
    return false;
  }
}

function isActive(pathname: string, item: NavItem): boolean {
  if (item.href === "/app" || item.href === "/admin") return pathname === item.href;
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

function NavList({
  items,
  pathname,
  collapsed,
  onNavigate,
}: {
  items: NavItem[];
  pathname: string;
  collapsed: boolean;
  onNavigate?: () => void;
}) {
  return (
    <ul className="space-y-1">
      {items.map((item) => {
        const active = isActive(pathname, item);
        return (
          <li key={item.href}>
            <Link
              href={item.href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              title={collapsed ? item.label : undefined}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors duration-150 outline-none focus-visible:ring-2 focus-visible:ring-ring",
                active
                  ? "bg-primary text-primary-fg"
                  : "text-muted hover:bg-surface-2 hover:text-text",
                collapsed && "justify-center px-2",
              )}
            >
              <item.icon aria-hidden className="size-4 shrink-0" />
              <span className={cn(collapsed && "sr-only")}>{item.label}</span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

function SidebarContent({
  collapsed,
  isStaff,
  onNavigate,
}: {
  collapsed: boolean;
  isStaff: boolean;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  return (
    <nav aria-label="Main" className="flex flex-1 flex-col gap-6 overflow-y-auto p-3">
      <NavList items={MAIN_NAV} pathname={pathname} collapsed={collapsed} onNavigate={onNavigate} />
      {isStaff && (
        <div className="space-y-2">
          <p
            className={cn(
              "px-3 text-xs font-medium tracking-wide text-muted uppercase",
              collapsed && "sr-only",
            )}
          >
            Admin
          </p>
          <NavList
            items={ADMIN_NAV}
            pathname={pathname}
            collapsed={collapsed}
            onNavigate={onNavigate}
          />
        </div>
      )}
    </nav>
  );
}

function Brand({ collapsed }: { collapsed?: boolean }) {
  return (
    <Link href="/app" className="flex items-center gap-2 px-1 text-text">
      <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-fg">
        <Network aria-hidden className="size-4" />
      </span>
      <span className={cn("text-lg font-semibold tracking-tight", collapsed && "sr-only")}>
        Cognexa
      </span>
    </Link>
  );
}

function UserMenu() {
  const { data: me } = useMe();
  const signOut = useSignOut();
  const router = useRouter();
  const name = me?.display_name ?? me?.email ?? "Account";
  const initial = name.trim().charAt(0).toUpperCase() || "?";
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label="Open user menu"
        className="flex size-9 items-center justify-center rounded-full bg-accent text-sm font-semibold text-bg outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        {initial}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuGroup>
          <DropdownMenuLabel className="space-y-0.5">
            <span className="block truncate text-sm font-medium text-text">{name}</span>
            {me?.email && (
              <span className="block truncate text-xs font-normal text-muted">{me.email}</span>
            )}
            {me && (
              <span className="mt-1 inline-block rounded-full border border-border px-2 py-0.5 text-[11px] font-normal text-muted capitalize">
                {me.role}
              </span>
            )}
          </DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <div className="px-2 py-1.5">
          <ThemeSwitcher className="w-full justify-between" />
        </div>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => router.push("/app/settings")}>
          <Settings aria-hidden /> Settings
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => void signOut()}>
          <LogOut aria-hidden /> Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const signOut = useSignOut();
  const { data: me, error, refetch } = useMe();
  const collapsed = useSyncExternalStore(subscribeCollapse, readCollapsed, () => false);
  const [drawer, setDrawer] = useState(false);

  useEffect(() => {
    if (!drawer) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setDrawer(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawer]);

  // First-time users go through onboarding before anything else.
  useEffect(() => {
    if (me && !me.onboarding_completed && pathname !== "/app/onboarding") {
      router.replace("/app/onboarding");
    }
  }, [me, pathname, router]);

  // A rejected session (revoked, deleted account) goes back to sign-in.
  useEffect(() => {
    if (error instanceof ApiError && error.status === 401) void signOut();
  }, [error, signOut]);

  function toggle() {
    try {
      localStorage.setItem(COLLAPSE_KEY, collapsed ? "0" : "1");
    } catch {
      // storage unavailable: the preference just won't persist
    }
    collapseListeners.forEach((l) => l());
  }

  const isStaff = me?.role === "admin" || me?.role === "reviewer";

  return (
    <div className="flex min-h-dvh flex-col bg-bg text-text">
      <ThemeSync />
      <WakingBanner />
      <div className="flex flex-1">
        <aside
          className={cn(
            "sticky top-0 hidden h-dvh shrink-0 flex-col border-r border-border bg-surface transition-[width] duration-200 md:flex",
            collapsed ? "w-16" : "w-60",
          )}
        >
          <div className="flex h-14 items-center border-b border-border px-3">
            <Brand collapsed={collapsed} />
          </div>
          <SidebarContent collapsed={collapsed} isStaff={isStaff} />
          <div className="border-t border-border p-3">
            <Button
              variant="ghost"
              size="sm"
              className="w-full justify-center"
              onClick={toggle}
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              {collapsed ? <ChevronsRight aria-hidden /> : <ChevronsLeft aria-hidden />}
              <span className={cn(collapsed && "sr-only")}>Collapse</span>
            </Button>
          </div>
        </aside>

        {drawer && (
          <div className="fixed inset-0 z-40 md:hidden">
            <button
              type="button"
              aria-label="Close menu"
              className="absolute inset-0 bg-bg/70 backdrop-blur-sm"
              onClick={() => setDrawer(false)}
            />
            <aside
              role="dialog"
              aria-modal="true"
              aria-label="Navigation"
              className="absolute inset-y-0 left-0 flex w-64 flex-col border-r border-border bg-surface"
            >
              <div className="flex h-14 items-center justify-between border-b border-border px-3">
                <Brand />
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setDrawer(false)}
                  aria-label="Close menu"
                >
                  <X aria-hidden />
                </Button>
              </div>
              <SidebarContent
                collapsed={false}
                isStaff={isStaff}
                onNavigate={() => setDrawer(false)}
              />
            </aside>
          </div>
        )}

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-border bg-bg/90 px-4 backdrop-blur">
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              onClick={() => setDrawer(true)}
              aria-label="Open menu"
            >
              <Menu aria-hidden />
            </Button>
            <ConceptSearch />
            <div className="ml-auto flex items-center gap-3">
              <UsageMeter className="hidden sm:flex" />
              <UserMenu />
            </div>
          </header>
          <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6">
            {error && !(error instanceof ApiError && error.status === 401) ? (
              <ErrorState
                title="Couldn't load your account"
                message={error.message}
                requestId={error instanceof ApiError ? error.requestId : undefined}
                onRetry={() => void refetch()}
              />
            ) : (
              children
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
