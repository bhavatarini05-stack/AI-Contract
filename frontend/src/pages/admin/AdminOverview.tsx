import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Activity, AlertOctagon, CalendarClock, FileStack, Gauge, ShieldCheck, Users } from "lucide-react";
import { api } from "../../api/client";
import type { Severity } from "../../api/types";
import { BarList, StatTile } from "../../components/charts";
import { Card, EmptyState, ErrorBox, PageHeader, SEVERITY, Skeleton, StatusPill, formatDate } from "../../components/ui";

const LEVELS: Severity[] = ["critical", "high", "medium", "low"];

export default function AdminOverview() {
  const q = useQuery({ queryKey: ["admin-stats"], queryFn: api.adminStats, refetchInterval: 15_000 });
  const s = q.data;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Admin overview"
        description="Organisation-wide activity across all users and contracts."
        actions={
          <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-soft px-3 py-1.5 text-xs font-semibold text-brand">
            <ShieldCheck className="h-4 w-4" /> Administrator
          </span>
        }
      />
      <ErrorBox error={q.error} />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {!s ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-[124px] rounded-xl" />)
        ) : (
          <>
            <StatTile label="Users" value={s.users} hint={`${s.active_users} active · ${s.admins} admin${s.admins === 1 ? "" : "s"}`} icon={Users} />
            <StatTile label="Contracts" value={s.contracts} hint={`${s.by_status.done ?? 0} analyzed · ${s.by_status.failed ?? 0} failed`} icon={FileStack} accent="good" />
            <StatTile label="Average risk score" value={s.avg_risk_score ?? "—"} hint="Across all analyzed contracts" icon={Gauge} accent="warning" />
            <StatTile label="Deadlines ≤ 30 days" value={s.deadlines_30d} hint="Open obligations, all users" icon={CalendarClock} accent="critical" />
          </>
        )}
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <Card title="Risk across the organisation" subtitle="Contracts by risk level" icon={AlertOctagon}>
          {s && Object.keys(s.by_risk_level).length ? (
            <BarList
              caption="Contracts by risk level"
              data={LEVELS.map((l) => {
                const I = SEVERITY[l].icon;
                return { key: l, label: SEVERITY[l].label, value: s.by_risk_level[l] ?? 0, fill: SEVERITY[l].bar, lead: <I className="h-4 w-4 text-muted" /> };
              })}
            />
          ) : (
            <EmptyState icon={Gauge} title="No analyses yet" />
          )}
        </Card>

        <Card
          title="Contracts per user"
          subtitle="Top uploaders"
          icon={Users}
          actions={
            <Link to="/admin/users" className="text-xs font-medium text-brand hover:underline">
              Manage users
            </Link>
          }
        >
          {s?.contracts_per_user.length ? (
            <BarList caption="Contracts per user" data={s.contracts_per_user.slice(0, 6).map((u) => ({ key: String(u.user_id), label: u.name, value: u.contracts }))} />
          ) : (
            <EmptyState icon={Users} title="No users yet" />
          )}
        </Card>

        <Card title="Recent activity" subtitle="Latest analysis jobs" icon={Activity} bodyClassName="p-0">
          {s?.recent_activity.length ? (
            <ul className="divide-y divide-line">
              {s.recent_activity.map((a) => (
                <li key={a.job_id} className="flex items-center gap-3 px-5 py-3">
                  <div className="min-w-0 flex-1">
                    <Link to={`/contracts/${a.contract_id}`} className="block truncate text-sm font-medium hover:text-brand">
                      {a.filename}
                    </Link>
                    <p className="truncate text-xs text-muted">
                      {a.owner ?? "Unassigned"} · {formatDate(a.created_at)}
                    </p>
                  </div>
                  <StatusPill status={a.status === "running" ? "processing" : a.status} label={a.status === "running" ? a.stage : undefined} />
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState icon={Activity} title="No activity yet" />
          )}
        </Card>
      </div>
    </div>
  );
}
