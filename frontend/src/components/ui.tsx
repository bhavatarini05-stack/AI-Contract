import type { ButtonHTMLAttributes, ComponentType, ReactNode } from "react";
import { AlertOctagon, AlertTriangle, CheckCircle2, Info, Loader2, type LucideProps } from "lucide-react";
import type { Severity } from "../api/types";

export type Icon = ComponentType<LucideProps>;

export const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(" ");

/* ---------- severity (status palette: always icon + label, never color alone) ---------- */

export const SEVERITY: Record<Severity, { label: string; icon: Icon; dot: string; tint: string; bar: string }> = {
  low: { label: "Low", icon: Info, dot: "bg-good", tint: "bg-good/10 ring-good/30", bar: "bg-good" },
  medium: { label: "Medium", icon: AlertTriangle, dot: "bg-warning", tint: "bg-warning/15 ring-warning/40", bar: "bg-warning" },
  high: { label: "High", icon: AlertTriangle, dot: "bg-serious", tint: "bg-serious/15 ring-serious/40", bar: "bg-serious" },
  critical: { label: "Critical", icon: AlertOctagon, dot: "bg-critical", tint: "bg-critical/10 ring-critical/30", bar: "bg-critical" },
};
const SEV_ICON_COLOR: Record<Severity, string> = {
  low: "text-good",
  medium: "text-warning",
  high: "text-serious",
  critical: "text-critical",
};

export function SeverityBadge({ severity, size = "sm" }: { severity: Severity | string; size?: "sm" | "md" }) {
  const s = SEVERITY[severity as Severity] ?? SEVERITY.low;
  const I = s.icon;
  return (
    <span
      className={cx(
        "inline-flex shrink-0 items-center gap-1 rounded-full font-medium text-ink ring-1 ring-inset",
        s.tint,
        size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs",
      )}
    >
      <I className={cx("h-3.5 w-3.5", SEV_ICON_COLOR[severity as Severity] ?? "text-good")} aria-hidden />
      {s.label}
    </span>
  );
}

export function RiskScore({ score, level }: { score: number | null; level: Severity | null }) {
  if (score === null || level === null) return <span className="text-muted">—</span>;
  return (
    <span className="inline-flex items-center gap-2">
      <span className="tnum w-7 text-right text-sm font-semibold">{score}</span>
      <span className="h-1.5 w-16 overflow-hidden rounded-full bg-track">
        <span className={cx("block h-full rounded-full", SEVERITY[level].bar)} style={{ width: `${score}%` }} />
      </span>
      <SeverityBadge severity={level} />
    </span>
  );
}

/* ---------- generic status pill ---------- */

const PILL: Record<string, string> = {
  done: "bg-good/10 ring-good/30",
  pass: "bg-good/10 ring-good/30",
  compliant: "bg-good/10 ring-good/30",
  same: "bg-good/10 ring-good/30",
  completed: "bg-good/10 ring-good/30",
  processing: "bg-brand/10 ring-brand/30",
  uploaded: "bg-brand/10 ring-brand/30",
  sent: "bg-brand/10 ring-brand/30",
  added: "bg-brand/10 ring-brand/30",
  unclear: "bg-warning/15 ring-warning/40",
  needs_review: "bg-warning/15 ring-warning/40",
  changed: "bg-warning/15 ring-warning/40",
  failed: "bg-critical/10 ring-critical/30",
  fail: "bg-critical/10 ring-critical/30",
  non_compliant: "bg-critical/10 ring-critical/30",
  missing: "bg-critical/10 ring-critical/30",
  declined: "bg-critical/10 ring-critical/30",
};
const PILL_DOT: Record<string, string> = {
  done: "bg-good", pass: "bg-good", compliant: "bg-good", same: "bg-good", completed: "bg-good",
  processing: "bg-brand", uploaded: "bg-brand", sent: "bg-brand", added: "bg-brand",
  unclear: "bg-warning", needs_review: "bg-warning", changed: "bg-warning",
  failed: "bg-critical", fail: "bg-critical", non_compliant: "bg-critical", missing: "bg-critical", declined: "bg-critical",
};

export function StatusPill({ status, label }: { status: string; label?: string }) {
  return (
    <span
      className={cx(
        "inline-flex shrink-0 items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium capitalize text-ink ring-1 ring-inset",
        PILL[status] ?? "bg-surface-2 ring-line",
      )}
    >
      <span className={cx("h-1.5 w-1.5 rounded-full", PILL_DOT[status] ?? "bg-muted", status === "processing" && "animate-pulse")} />
      {label ?? status.replace(/_/g, " ")}
    </span>
  );
}

export function Chip({ icon: I, children }: { icon?: Icon; children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-md bg-surface-2 px-2 py-1 text-xs text-ink-2 ring-1 ring-inset ring-line">
      {I && <I className="h-3.5 w-3.5 text-muted" aria-hidden />}
      {children}
    </span>
  );
}

/* ---------- layout primitives ---------- */

export function Card({
  title,
  subtitle,
  icon: I,
  actions,
  children,
  className,
  bodyClassName,
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  icon?: Icon;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section className={cx("animate-fade-in rounded-xl border border-line bg-surface shadow-card", className)}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 border-b border-line px-5 py-3.5">
          <div className="flex min-w-0 items-center gap-2.5">
            {I && (
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-brand-soft text-brand">
                <I className="h-4 w-4" aria-hidden />
              </span>
            )}
            <div className="min-w-0">
              {title && <h2 className="truncate text-sm font-semibold">{title}</h2>}
              {subtitle && <p className="truncate text-xs text-muted">{subtitle}</p>}
            </div>
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={cx("p-5", bodyClassName)}>{children}</div>
    </section>
  );
}

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-1 text-sm text-ink-2">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

type BtnVariant = "primary" | "secondary" | "ghost" | "danger";
export function Button({
  children,
  variant = "primary",
  icon: I,
  loading,
  size = "md",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: BtnVariant; icon?: Icon; loading?: boolean; size?: "sm" | "md" }) {
  const v: Record<BtnVariant, string> = {
    primary: "bg-gradient-to-b from-grad-a to-grad-b text-white shadow-sm hover:brightness-110",
    secondary: "bg-surface text-ink ring-1 ring-inset ring-line hover:bg-surface-2",
    ghost: "text-ink-2 hover:bg-surface-2 hover:text-ink",
    danger: "bg-surface text-critical ring-1 ring-inset ring-critical/30 hover:bg-critical/10",
  };
  return (
    <button
      {...props}
      disabled={props.disabled || loading}
      className={cx(
        "inline-flex items-center justify-center gap-1.5 rounded-lg font-medium transition disabled:cursor-not-allowed disabled:opacity-50",
        size === "sm" ? "px-2.5 py-1 text-xs" : "px-3.5 py-2 text-sm",
        v[variant],
        className,
      )}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : I ? <I className={size === "sm" ? "h-3.5 w-3.5" : "h-4 w-4"} /> : null}
      {children}
    </button>
  );
}

export function Tabs<T extends string>({
  tabs,
  value,
  onChange,
}: {
  tabs: { id: T; label: string; icon?: Icon; count?: number }[];
  value: T;
  onChange: (t: T) => void;
}) {
  return (
    <div className="flex gap-1 overflow-x-auto rounded-xl border border-line bg-surface p-1 shadow-card" role="tablist">
      {tabs.map(({ id, label, icon: I, count }) => (
        <button
          key={id}
          role="tab"
          aria-selected={value === id}
          onClick={() => onChange(id)}
          className={cx(
            "flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition",
            value === id ? "bg-brand-soft font-medium text-brand" : "text-ink-2 hover:bg-surface-2 hover:text-ink",
          )}
        >
          {I && <I className="h-4 w-4" />}
          {label}
          {count !== undefined && count > 0 && (
            <span className={cx("tnum rounded-full px-1.5 text-[10px] font-semibold", value === id ? "bg-brand text-white" : "bg-surface-2 text-ink-2")}>
              {count}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

export function PageLink({ page, onClick }: { page: number | null; onClick?: (p: number) => void }) {
  if (!page) return null;
  return (
    <button
      onClick={() => onClick?.(page)}
      className="tnum shrink-0 rounded-md px-1.5 py-0.5 text-[11px] font-medium text-brand ring-1 ring-inset ring-brand/30 hover:bg-brand-soft"
      title="Show in document"
    >
      p.{page}
    </button>
  );
}

export function ErrorBox({ error }: { error: unknown }) {
  if (!error) return null;
  return (
    <div className="flex items-start gap-2 rounded-lg bg-critical/10 p-3 text-sm text-ink ring-1 ring-inset ring-critical/30">
      <AlertOctagon className="mt-0.5 h-4 w-4 shrink-0 text-critical" />
      <span className="min-w-0 break-words">{error instanceof Error ? error.message : String(error)}</span>
    </div>
  );
}

export function Notice({ tone = "warning", children }: { tone?: "warning" | "info" | "good"; children: ReactNode }) {
  const t = {
    warning: { c: "bg-warning/10 ring-warning/40", i: <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" /> },
    info: { c: "bg-brand/5 ring-brand/20", i: <Info className="mt-0.5 h-4 w-4 shrink-0 text-brand" /> },
    good: { c: "bg-good/10 ring-good/30", i: <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-good" /> },
  }[tone];
  return (
    <div className={cx("flex items-start gap-2 rounded-lg p-3 text-sm text-ink ring-1 ring-inset", t.c)}>
      {t.i}
      <div className="min-w-0">{children}</div>
    </div>
  );
}

export function EmptyState({
  icon: I = Info,
  title,
  description,
  action,
}: {
  icon?: Icon;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-10 text-center">
      <span className="mb-3 grid h-12 w-12 place-items-center rounded-2xl bg-brand-soft text-brand">
        <I className="h-6 w-6" />
      </span>
      <p className="text-sm font-semibold">{title}</p>
      {description && <p className="mt-1 max-w-sm text-sm text-ink-2">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return (
    <div className={cx("relative overflow-hidden rounded-md bg-surface-2", className)}>
      <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-line/60 to-transparent" />
    </div>
  );
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={cx("input w-auto py-1.5 pr-8", props.className)} />;
}

export function formatDate(d: string | null | undefined) {
  if (!d) return "—";
  return new Date(d.length === 10 ? d + "T00:00:00" : d).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export function relativeDays(days: number | null | undefined) {
  if (days === null || days === undefined) return "";
  if (days < 0) return `${-days}d overdue`;
  if (days === 0) return "today";
  if (days === 1) return "tomorrow";
  return `in ${days}d`;
}
