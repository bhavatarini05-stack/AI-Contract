import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  BookOpenCheck,
  ChevronDown,
  FolderKanban,
  LogOut,
  UserCog,
  UserRound,
  Users,
  CalendarClock,
  Cpu,
  FileStack,
  FileText,
  LayoutDashboard,
  Menu,
  Moon,
  ScrollText,
  Search,
  Settings,
  ShieldCheck,
  Sun,
  UploadCloud,
  X,
} from "lucide-react";
import { api } from "../api/client";
import { initials, useAuth } from "../lib/auth";
import { useTheme } from "../lib/theme";
import { cx, type Icon } from "./ui";

const NAV: { to: string; label: string; icon: Icon; section?: string }[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, section: "Workspace" },
  { to: "/contracts", label: "Contracts", icon: FileStack },
  { to: "/upload", label: "Upload & Analyze", icon: UploadCloud },
  { to: "/obligations", label: "Obligations", icon: CalendarClock },
  { to: "/templates", label: "Templates", icon: ScrollText, section: "Knowledge" },
  { to: "/policies", label: "Policies", icon: ShieldCheck },
  { to: "/settings", label: "Settings", icon: Settings, section: "System" },
];

const ADMIN_NAV: { to: string; label: string; icon: Icon; section?: string }[] = [
  { to: "/admin", label: "Admin overview", icon: Activity, section: "Administration" },
  { to: "/admin/users", label: "Users", icon: Users },
  { to: "/admin/contracts", label: "All contracts", icon: FolderKanban },
];

export function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2.5">
      <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-grad-a to-grad-b text-white shadow-sm">
        <BookOpenCheck className="h-5 w-5" />
      </span>
      <span className="leading-tight">
        <span className="block text-[15px] font-semibold tracking-tight">ClauseLens</span>
        <span className="block text-[11px] text-muted">AI contract analyzer</span>
      </span>
    </Link>
  );
}

function Sidebar({ onNavigate, unread }: { onNavigate?: () => void; unread: number }) {
  const { isAdmin } = useAuth();
  const items = isAdmin ? [...NAV, ...ADMIN_NAV] : NAV;
  return (
    <nav className="flex h-full flex-col gap-1 px-3 py-5">
      <div className="mb-5 px-2">
        <Logo />
      </div>
      {items.map(({ to, label, icon: I, section }) => (
        <div key={to}>
          {section && <p className="mb-1 mt-4 px-3 text-[11px] font-semibold uppercase tracking-wider text-muted first:mt-0">{section}</p>}
          <NavLink
            to={to}
            end={to === "/" || to === "/admin"}
            onClick={onNavigate}
            className={({ isActive }) =>
              cx(
                "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition",
                isActive ? "bg-brand-soft font-medium text-brand" : "text-ink-2 hover:bg-surface-2 hover:text-ink",
              )
            }
          >
            <I className="h-[18px] w-[18px]" />
            <span className="flex-1">{label}</span>
            {to === "/obligations" && unread > 0 && (
              <span className="tnum rounded-full bg-critical px-1.5 text-[10px] font-semibold text-white">{unread}</span>
            )}
          </NavLink>
        </div>
      ))}
    </nav>
  );
}

export function Avatar({ name, size = "md" }: { name: string; size?: "sm" | "md" | "lg" }) {
  return (
    <span
      className={cx(
        "grid shrink-0 place-items-center rounded-full bg-gradient-to-br from-grad-a to-grad-b font-semibold text-white",
        size === "sm" ? "h-7 w-7 text-[11px]" : size === "lg" ? "h-14 w-14 text-lg" : "h-9 w-9 text-xs",
      )}
      aria-hidden
    >
      {initials(name)}
    </span>
  );
}

function UserMenu() {
  const { user, isAdmin, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const location = useLocation();

  useEffect(() => setOpen(false), [location.pathname]);
  useEffect(() => {
    const close = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  if (!user) return null;
  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-lg border border-line bg-surface py-1 pl-1 pr-2 hover:bg-surface-2"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <Avatar name={user.name} size="sm" />
        <span className="hidden max-w-[140px] truncate text-sm font-medium md:block">{user.name}</span>
        <ChevronDown className={cx("h-4 w-4 text-muted transition", open && "rotate-180")} />
      </button>
      {open && (
        <div role="menu" className="absolute right-0 top-full z-30 mt-2 w-64 animate-fade-in overflow-hidden rounded-xl border border-line bg-surface shadow-pop">
          <div className="flex items-center gap-3 border-b border-line p-4">
            <Avatar name={user.name} />
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">{user.name}</p>
              <p className="truncate text-xs text-muted">{user.email}</p>
              <span
                className={cx(
                  "mt-1 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                  isAdmin ? "bg-brand-soft text-brand" : "bg-surface-2 text-ink-2",
                )}
              >
                {isAdmin ? <ShieldCheck className="h-3 w-3" /> : <UserRound className="h-3 w-3" />}
                {user.role}
              </span>
            </div>
          </div>
          <div className="p-1.5">
            <Link to="/profile" role="menuitem" className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm hover:bg-surface-2">
              <UserCog className="h-4 w-4 text-muted" /> Profile &amp; password
            </Link>
            {isAdmin && (
              <Link to="/admin" role="menuitem" className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm hover:bg-surface-2">
                <Activity className="h-4 w-4 text-muted" /> Admin panel
              </Link>
            )}
            <button
              role="menuitem"
              onClick={logout}
              className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-critical hover:bg-critical/10"
            >
              <LogOut className="h-4 w-4" /> Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function AiStatus() {
  const health = useQuery({ queryKey: ["health"], queryFn: api.health, refetchInterval: 30_000 });
  const ok = health.data?.llm.ok;
  return (
    <Link
      to="/settings"
      className="hidden items-center gap-2 rounded-lg border border-line bg-surface px-2.5 py-1.5 text-xs text-ink-2 hover:bg-surface-2 sm:flex"
      title={ok ? "Local LLM connected" : health.data?.llm.hint ?? "Local LLM unavailable"}
    >
      <Cpu className="h-3.5 w-3.5" />
      <span className={cx("h-2 w-2 rounded-full", health.isLoading ? "bg-muted" : ok ? "bg-good" : "bg-warning")} />
      {health.data ? (ok ? health.data.llm.model : "Rule-based mode") : "Checking…"}
    </Link>
  );
}

function GlobalSearch() {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLInputElement>(null);
  const contracts = useQuery({ queryKey: ["contracts"], queryFn: api.listContracts });
  const results = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return [];
    return (contracts.data ?? [])
      .filter((c) => [c.filename, c.contract_type, c.governing_law].some((v) => v?.toLowerCase().includes(s)))
      .slice(0, 6);
  }, [q, contracts.data]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        ref.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="relative w-full max-w-md">
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
      <input
        ref={ref}
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        placeholder="Search contracts…"
        className="input pl-9 pr-14"
        aria-label="Search contracts"
      />
      <kbd className="pointer-events-none absolute right-2.5 top-1/2 hidden -translate-y-1/2 rounded border border-line bg-surface-2 px-1.5 text-[10px] text-muted sm:block">
        Ctrl K
      </kbd>
      {open && q && (
        <div className="absolute left-0 right-0 top-full z-30 mt-1 overflow-hidden rounded-xl border border-line bg-surface shadow-pop">
          {results.length === 0 ? (
            <p className="px-3 py-3 text-sm text-muted">No matching contracts</p>
          ) : (
            results.map((c) => (
              <button
                key={c.id}
                onMouseDown={() => {
                  navigate(`/contracts/${c.id}`);
                  setQ("");
                }}
                className="flex w-full items-center gap-3 px-3 py-2 text-left text-sm hover:bg-surface-2"
              >
                <FileText className="h-4 w-4 shrink-0 text-muted" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-medium">{c.filename}</span>
                  <span className="block truncate text-xs text-muted">{[c.contract_type, c.governing_law].filter(Boolean).join(" · ")}</span>
                </span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default function Layout({ children }: { children: ReactNode }) {
  const { theme, toggle } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const alerts = useQuery({ queryKey: ["alerts"], queryFn: () => api.listAlerts(true), refetchInterval: 60_000 });

  useEffect(() => setMobileOpen(false), [location.pathname]);

  return (
    <div className="min-h-screen">
      {/* desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 border-r border-line bg-surface lg:block">
        <Sidebar unread={alerts.data?.length ?? 0} />
      </aside>

      {/* mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-ink/40" onClick={() => setMobileOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-72 animate-fade-in bg-surface shadow-pop">
            <button className="absolute right-3 top-4 rounded-lg p-1.5 hover:bg-surface-2" onClick={() => setMobileOpen(false)} aria-label="Close menu">
              <X className="h-5 w-5" />
            </button>
            <Sidebar unread={alerts.data?.length ?? 0} onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      )}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-10 flex h-16 items-center gap-3 border-b border-line bg-page/80 px-4 backdrop-blur sm:px-6">
          <button className="rounded-lg p-2 hover:bg-surface-2 lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Open menu">
            <Menu className="h-5 w-5" />
          </button>
          <GlobalSearch />
          <div className="ml-auto flex items-center gap-2">
            <AiStatus />
            <button
              onClick={toggle}
              className="grid h-9 w-9 place-items-center rounded-lg border border-line bg-surface text-ink-2 hover:bg-surface-2 hover:text-ink"
              aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
              title="Toggle theme"
            >
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
            <UserMenu />
          </div>
        </header>
        <main className="mx-auto max-w-[1400px] px-4 py-6 sm:px-6 lg:py-8">{children}</main>
        <footer className="px-6 pb-6 text-center text-xs text-muted">
          ClauseLens runs on free, local open-source models · AI-generated analysis is not legal advice.
        </footer>
      </div>
    </div>
  );
}
