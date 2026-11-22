import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarClock, Check, FileText, RotateCcw, X } from "lucide-react";
import { api } from "../api/client";
import type { Obligation } from "../api/types";
import { StatTile } from "../components/charts";
import { Button, Card, EmptyState, ErrorBox, PageHeader, Select, Skeleton, StatusPill, cx, formatDate, relativeDays } from "../components/ui";
import { AlarmClock, CalendarX, Repeat } from "lucide-react";

const WINDOWS = [
  ["30", "Next 30 days"],
  ["90", "Next 90 days"],
  ["365", "Next 12 months"],
  ["", "All dates"],
] as const;

function monthKey(o: Obligation) {
  if (!o.due_date) return "Ongoing (no fixed date)";
  return new Date(o.due_date + "T00:00:00").toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

export default function Obligations() {
  const qc = useQueryClient();
  const [days, setDays] = useState<string>("365");
  const [status, setStatus] = useState("open");
  const q = useQuery({
    queryKey: ["obligations", days, status],
    queryFn: () => api.listObligations(days ? Number(days) : undefined, status),
  });
  const all = useQuery({ queryKey: ["obligations", "", "open"], queryFn: () => api.listObligations(undefined, "open") });
  const update = useMutation({
    mutationFn: ({ id, s }: { id: number; s: string }) => api.updateObligation(id, s),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["obligations"] }),
  });

  const groups = useMemo(() => {
    const m = new Map<string, Obligation[]>();
    (q.data ?? []).forEach((o) => m.set(monthKey(o), [...(m.get(monthKey(o)) ?? []), o]));
    return [...m.entries()];
  }, [q.data]);

  const open = all.data ?? [];
  const overdue = open.filter((o) => (o.days_left ?? 1) < 0).length;
  const in30 = open.filter((o) => o.days_left != null && o.days_left >= 0 && o.days_left <= 30).length;
  const renewals = open.filter((o) => o.kind === "renewal_notice").length;

  return (
    <div>
      <PageHeader title="Obligations & deadlines" description="Renewal notices, expiries and duties extracted from your contracts." />

      <div className="mb-6 grid gap-4 sm:grid-cols-3">
        <StatTile label="Overdue" value={overdue} icon={AlarmClock} accent="critical" hint="Past their due date" />
        <StatTile label="Due in 30 days" value={in30} icon={CalendarX} accent="warning" hint="Act on these soon" />
        <StatTile label="Renewal notices" value={renewals} icon={Repeat} hint="Auto-renewal deadlines tracked" />
      </div>

      <Card
        title="Timeline"
        icon={CalendarClock}
        actions={
          <>
            <Select value={days} onChange={(e) => setDays(e.target.value)} aria-label="Time window">
              {WINDOWS.map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </Select>
            <Select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
              <option value="open">Open</option>
              <option value="done">Done</option>
              <option value="dismissed">Dismissed</option>
            </Select>
          </>
        }
      >
        <ErrorBox error={q.error} />
        {q.isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-16" />
            ))}
          </div>
        ) : !groups.length ? (
          <EmptyState icon={CalendarClock} title="Nothing here" description="No obligations match this window and status." />
        ) : (
          <div className="space-y-8">
            {groups.map(([month, items]) => (
              <section key={month}>
                <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted">{month}</h3>
                <ul className="space-y-2">
                  {items.map((o) => {
                    const late = (o.days_left ?? 1) < 0;
                    const soon = o.days_left != null && o.days_left <= 30;
                    return (
                      <li key={o.id} className="flex flex-wrap items-center gap-4 rounded-xl border border-line p-3 transition hover:bg-surface-2">
                        <div
                          className={cx(
                            "grid h-14 w-14 shrink-0 place-items-center rounded-xl text-center",
                            !o.due_date ? "bg-surface-2" : late ? "bg-critical/10" : soon ? "bg-serious/15" : "bg-brand-soft",
                          )}
                        >
                          {o.due_date ? (
                            <span>
                              <span className="block text-[10px] font-semibold uppercase text-ink-2">
                                {new Date(o.due_date + "T00:00:00").toLocaleDateString(undefined, { month: "short" })}
                              </span>
                              <span className="tnum block text-lg font-semibold leading-none">{new Date(o.due_date + "T00:00:00").getDate()}</span>
                            </span>
                          ) : (
                            <Repeat className="h-5 w-5 text-muted" />
                          )}
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium">{o.description}</p>
                          <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted">
                            <StatusPill status={late ? "failed" : "uploaded"} label={o.kind.replace("_", " ")} />
                            <Link to={`/contracts/${o.contract_id}`} className="inline-flex items-center gap-1 hover:text-brand">
                              <FileText className="h-3.5 w-3.5" />
                              {o.contract_filename}
                            </Link>
                            {o.due_date && (
                              <span className={cx("font-medium", late ? "text-critical" : "text-ink-2")}>
                                {formatDate(o.due_date)} · {relativeDays(o.days_left)}
                              </span>
                            )}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          {status === "open" ? (
                            <>
                              <Button size="sm" variant="secondary" icon={Check} onClick={() => update.mutate({ id: o.id, s: "done" })}>
                                Done
                              </Button>
                              <Button size="sm" variant="ghost" icon={X} onClick={() => update.mutate({ id: o.id, s: "dismissed" })}>
                                Dismiss
                              </Button>
                            </>
                          ) : (
                            <Button size="sm" variant="secondary" icon={RotateCcw} onClick={() => update.mutate({ id: o.id, s: "open" })}>
                              Reopen
                            </Button>
                          )}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </section>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
