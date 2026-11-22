/*
 * Small, dependency-free chart pieces following the dataviz method:
 *  - Stat tiles for headline numbers (not one-bar charts)
 *  - Meter for a single ratio against a limit (risk score / 100)
 *  - Ranked horizontal bar list for part-to-whole / magnitude (not donuts)
 * Thin marks, 4px rounded ends, recessive track, values in ink (never series color),
 * hover tooltips on every mark, and a visually hidden table for screen readers.
 */
import { useState, type ReactNode } from "react";
import { cx, type Icon } from "./ui";

export function StatTile({
  label,
  value,
  hint,
  icon: I,
  accent = "brand",
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  icon: Icon;
  accent?: "brand" | "critical" | "warning" | "good";
}) {
  const a = {
    brand: "bg-brand-soft text-brand",
    critical: "bg-critical/10 text-critical",
    warning: "bg-warning/15 text-warning",
    good: "bg-good/10 text-good",
  }[accent];
  return (
    <div className="animate-fade-in rounded-xl border border-line bg-surface p-5 shadow-card">
      <div className="flex items-start justify-between">
        <p className="text-sm font-medium text-ink-2">{label}</p>
        <span className={cx("grid h-9 w-9 place-items-center rounded-lg", a)}>
          <I className="h-[18px] w-[18px]" aria-hidden />
        </span>
      </div>
      <p className="mt-2 text-3xl font-semibold tracking-tight">{value}</p>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}

/** Single ratio against a limit. `fill` is a Tailwind bg class (status color for risk). */
export function Meter({ value, max = 100, fill, label }: { value: number; max?: number; fill: string; label: string }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div
      className="h-2 w-full overflow-hidden rounded-full bg-track"
      role="meter"
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={value}
      aria-label={label}
      title={`${label}: ${value}/${max}`}
    >
      <div className={cx("h-full rounded-full transition-[width] duration-700", fill)} style={{ width: `${pct}%` }} />
    </div>
  );
}

export interface BarDatum {
  key: string;
  label: ReactNode;
  value: number;
  /** Tailwind bg class; defaults to the single sequential hue */
  fill?: string;
  /** leading visual (e.g. severity icon) so identity never relies on color alone */
  lead?: ReactNode;
}

/** Ranked horizontal bars on a shared baseline, one row per part, value printed in ink. */
export function BarList({ data, unit = "", caption }: { data: BarDatum[]; unit?: string; caption: string }) {
  const [hover, setHover] = useState<string | null>(null);
  const max = Math.max(1, ...data.map((d) => d.value));
  const total = data.reduce((s, d) => s + d.value, 0);
  return (
    <figure>
      <ul className="space-y-3">
        {data.map((d) => {
          const pct = (d.value / max) * 100;
          const share = total ? Math.round((d.value / total) * 100) : 0;
          return (
            <li
              key={d.key}
              className="group relative"
              onMouseEnter={() => setHover(d.key)}
              onMouseLeave={() => setHover(null)}
            >
              <div className="mb-1 flex items-center justify-between gap-2 text-sm">
                <span className="flex min-w-0 items-center gap-2 text-ink-2">
                  {d.lead}
                  <span className="truncate">{d.label}</span>
                </span>
                <span className="tnum font-semibold text-ink">
                  {d.value}
                  {unit}
                </span>
              </div>
              <div className="h-2 w-full rounded-full bg-track/60">
                <div
                  className={cx("h-full rounded-[4px] transition-[width] duration-700", d.fill ?? "bg-series", hover && hover !== d.key && "opacity-50")}
                  style={{ width: `${Math.max(pct, d.value ? 2 : 0)}%` }}
                />
              </div>
              {hover === d.key && (
                <div className="pointer-events-none absolute -top-9 right-0 z-10 rounded-md bg-ink px-2 py-1 text-xs text-page shadow-pop">
                  {d.value}
                  {unit} · {share}% of total
                </div>
              )}
            </li>
          );
        })}
      </ul>
      {/* table view for assistive tech */}
      <table className="sr-only">
        <caption>{caption}</caption>
        <tbody>
          {data.map((d) => (
            <tr key={d.key}>
              <th>{typeof d.label === "string" ? d.label : d.key}</th>
              <td>
                {d.value}
                {unit}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
