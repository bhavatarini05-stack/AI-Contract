import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertOctagon,
  ArrowRight,
  BellRing,
  CalendarClock,
  FileStack,
  Gauge,
  Layers,
  ShieldAlert,
  Sparkles,
  UploadCloud,
  X,
} from "lucide-react";
import { api } from "../api/client";
import type { Severity } from "../api/types";
import { BarList, StatTile } from "../components/charts";
import { useAuth } from "../lib/auth";
import { Button, Card, EmptyState, ErrorBox, RiskScore, SEVERITY, Skeleton, StatusPill, cx, formatDate, relativeDays } from "../components/ui";

const LEVELS: Severity[] = ["critical", "high", "medium", "low"];

export default function Dashboard() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const contracts = useQuery({
    queryKey: ["contracts"],
    queryFn: api.listContracts,
    refetchInterval: (q) => (q.state.data?.some((c) => c.status === "processing" || c.status === "uploaded") ? 2000 : false),
  });
  const alerts = useQuery({ queryKey: ["alerts"], queryFn: () => api.listAlerts(true) });
  const upcoming = useQuery({ queryKey: ["obligations", "90", "open"], queryFn: () => api.listObligations(90) });
  const markRead = useMutation({
    mutationFn: api.markAlertRead,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });

  const all = contracts.data ?? [];
  const analysed = all.filter((c) => c.status === "done" && c.risk_score !== null);
  const highRisk = analysed.filter((c) => c.risk_level === "high" || c.risk_level === "critical").length;
  const avg = analysed.length ? Math.round(analysed.reduce((s, c) => s + (c.risk_score ?? 0), 0) / analysed.length) : null;
  const due30 = (upcoming.data ?? []).filter((o) => o.days_left !== null && o.days_left !== undefined && o.days_left <= 30).length;

  const byLevel = LEVELS.map((lvl) => {
    const S = SEVERITY[lvl];
    const I = S.icon;
    return {
      key: lvl,
      label: S.label,
      value: analysed.filter((c) => c.risk_level === lvl).length,
      fill: S.bar,
      lead: <I className="h-4 w-4 text-muted" aria-hidden />,
    };
  });

  const typeCounts = new Map<string, number>();
  analysed.forEach((c) => typeCounts.set(c.contract_type ?? "Other", (typeCounts.get(c.contract_type ?? "Other") ?? 0) + 1));
  const sortedTypes = [...typeCounts.entries()].sort((a, b) => b[1] - a[1]);
  const byType = [
    ...sortedTypes.slice(0, 5).map(([k, v]) => ({ key: k, label: k, value: v })),
    ...(sortedTypes.length > 5 ? [{ key: "other", label: "Other", value: sortedTypes.slice(5).reduce((s, [, v]) => s + v, 0) }] : []),
  ];

  return (
    <div className="space-y-6">
      {/* hero */}
      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-grad-a to-grad-b p-6 text-white shadow-pop sm:p-8">
        <div className="absolute -right-16 -top-16 h-64 w-64 rounded-full bg-white/10 blur-2xl" aria-hidden />
        <div className="absolute -bottom-24 right-40 h-56 w-56 rounded-full bg-white/10 blur-2xl" aria-hidden />
        <div className="relative flex flex-wrap items-center justify-between gap-6">
          <div className="max-w-xl">
            <p className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-2.5 py-1 text-xs font-medium">
              <Sparkles className="h-3.5 w-3.5" /> Welcome back, {user?.name.split(" ")[0]}
            </p>
            <h1 className="mt-3 text-2xl font-semibold tracking-tight sm:text-3xl">Review contracts in minutes, not hours.</h1>
            <p className="mt-2 text-sm text-white/80">
              Upload a PDF — ClauseLens extracts key clauses and terms, flags risks, tracks deadlines and explains it all in plain language.
            </p>
          </div>
          <Link to="/upload">
            <button className="inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-semibold text-grad-a shadow-sm transition hover:bg-white/90">
              <UploadCloud className="h-4 w-4" /> Analyze a contract
            </button>
          </Link>
        </div>
      </section>

      <ErrorBox error={contracts.error} />

      {/* expiry / renewal alerts */}
      {!!alerts.data?.length && (
        <section className="animate-fade-in overflow-hidden rounded-xl border border-warning/40 bg-surface shadow-card">
          <header className="flex items-center gap-2 border-b border-line bg-warning/10 px-5 py-2.5 text-sm font-semibold">
            <BellRing className="h-4 w-4 text-warning" /> {alerts.data.length} alert{alerts.data.length > 1 ? "s" : ""} need your attention
          </header>
          <ul className="divide-y divide-line">
            {alerts.data.slice(0, 4).map((a) => (
              <li key={a.id} className="group flex items-center gap-3 px-5 py-2.5">
                <Link to={`/contracts/${a.contract_id}`} className="min-w-0 flex-1 truncate text-sm hover:text-brand">
                  {a.message}
                </Link>
                <span className="hidden text-xs text-muted sm:inline">{formatDate(a.created_at)}</span>
                <button
                  onClick={() => markRead.mutate(a.id)}
                  className="rounded-md p-1 text-muted hover:bg-surface-2 hover:text-ink"
                  aria-label="Dismiss alert"
                >
                  <X className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* KPI row */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {contracts.isLoading ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-[124px] rounded-xl" />)
        ) : (
          <>
            <StatTile label="Contracts analyzed" value={analysed.length} hint={`${all.length} uploaded in total`} icon={FileStack} />
            <StatTile label="High / critical risk" value={highRisk} hint="Need attention before signing" icon={ShieldAlert} accent="critical" />
            <StatTile label="Average risk score" value={avg ?? "—"} hint="0 = clean · 100 = very risky" icon={Gauge} accent="warning" />
            <StatTile label="Deadlines ≤ 30 days" value={due30} hint="Renewals, notices & expiries" icon={CalendarClock} accent="good" />
          </>
        )}
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <Card title="Risk distribution" subtitle="Analyzed contracts by overall risk level" icon={AlertOctagon}>
          {analysed.length ? (
            <BarList data={byLevel} caption="Contracts by risk level" />
          ) : (
            <EmptyState icon={Gauge} title="No data yet" description="Risk levels appear after your first analysis." />
          )}
        </Card>
        <Card title="Contract types" subtitle="Detected by the classifier" icon={Layers}>
          {byType.length ? (
            <BarList data={byType} caption="Contracts by type" />
          ) : (
            <EmptyState icon={Layers} title="No data yet" description="Contract types appear after analysis." />
          )}
        </Card>
        <Card
          title="Upcoming deadlines"
          subtitle="Next 90 days"
          icon={CalendarClock}
          actions={
            <Link to="/obligations" className="text-xs font-medium text-brand hover:underline">
              View all
            </Link>
          }
          bodyClassName="p-0"
        >
          {upcoming.data?.length ? (
            <ol className="relative max-h-80 overflow-y-auto px-5 py-4">
              {upcoming.data.slice(0, 8).map((o) => {
                const late = (o.days_left ?? 0) < 0;
                const soon = (o.days_left ?? 99) <= 30;
                return (
                  <li key={o.id} className="relative flex gap-3 pb-4 last:pb-0">
                    <span className="absolute left-[7px] top-5 h-full w-px bg-line last:hidden" aria-hidden />
                    <span
                      className={cx(
                        "relative mt-1 h-[15px] w-[15px] shrink-0 rounded-full border-[3px] border-surface ring-2",
                        late ? "bg-critical ring-critical/40" : soon ? "bg-serious ring-serious/40" : "bg-series ring-series/30",
                      )}
                    />
                    <Link to={`/contracts/${o.contract_id}`} className="min-w-0 flex-1 rounded-md hover:bg-surface-2">
                      <p className="flex items-center gap-2 text-xs">
                        <span className="tnum font-semibold">{formatDate(o.due_date)}</span>
                        <span className={cx("font-medium", late ? "text-critical" : "text-ink-2")}>{relativeDays(o.days_left)}</span>
                      </p>
                      <p className="mt-0.5 line-clamp-2 text-sm">{o.description}</p>
                      <p className="truncate text-xs text-muted">{o.contract_filename}</p>
                    </Link>
                  </li>
                );
              })}
            </ol>
          ) : (
            <EmptyState icon={CalendarClock} title="Nothing due soon" description="Deadlines extracted from your contracts show up here." />
          )}
        </Card>
      </div>

      <div>
        <Card
          title="Recent contracts"
          icon={FileStack}
          actions={
            <Link to="/contracts" className="inline-flex items-center gap-1 text-xs font-medium text-brand hover:underline">
              All contracts <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          }
          bodyClassName="p-0"
        >
          {contracts.isLoading ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-10" />
              ))}
            </div>
          ) : all.length === 0 ? (
            <EmptyState
              icon={UploadCloud}
              title="No contracts yet"
              description="Upload your first contract PDF to see the analysis."
              action={
                <Link to="/upload">
                  <Button icon={UploadCloud}>Upload contract</Button>
                </Link>
              }
            />
          ) : (
            <ContractTable rows={all.slice(0, 6)} />
          )}
        </Card>

      </div>
    </div>
  );
}

export function ContractTable({ rows }: { rows: import("../api/types").ContractSummary[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-line text-left text-[11px] font-semibold uppercase tracking-wider text-muted">
            <th className="px-5 py-3">Contract</th>
            <th className="px-3 py-3">Type</th>
            <th className="whitespace-nowrap px-3 py-3">Governing law</th>
            <th className="px-3 py-3">Expires</th>
            <th className="px-3 py-3">Risk</th>
            <th className="px-5 py-3">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {rows.map((c) => (
            <tr key={c.id} className="transition hover:bg-surface-2">
              <td className="max-w-[280px] px-5 py-3">
                <Link to={`/contracts/${c.id}`} className="block truncate font-medium hover:text-brand">
                  {c.filename}
                </Link>
                <span className="text-xs text-muted">
                  {[c.page_count && `${c.page_count} pages`, c.language?.toUpperCase(), formatDate(c.uploaded_at)].filter(Boolean).join(" · ")}
                </span>
              </td>
              <td className="whitespace-nowrap px-3 py-3 text-ink-2">{c.contract_type ?? "—"}</td>
              <td className="whitespace-nowrap px-3 py-3 text-ink-2">{c.governing_law ?? "—"}</td>
              <td className="tnum whitespace-nowrap px-3 py-3 text-ink-2">{formatDate(c.expiry_date)}</td>
              <td className="whitespace-nowrap px-3 py-3">
                <RiskScore score={c.risk_score} level={c.risk_level} />
              </td>
              <td className="px-5 py-3">
                <StatusPill status={c.status} label={c.status === "done" ? "analyzed" : undefined} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
