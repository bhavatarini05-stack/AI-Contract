import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  Banknote,
  BellRing,
  BookText,
  CalendarCheck,
  CalendarClock,
  CalendarX,
  ChevronDown,
  Clock,
  Eye,
  EyeOff,
  FileSignature,
  FileText,
  GitCompareArrows,
  Handshake,
  Landmark,
  Languages,
  Lightbulb,
  ListTree,
  Quote,
  RefreshCw,
  Repeat,
  Scale,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Trash2,
  Users,
  Wallet,
} from "lucide-react";
import { api } from "../api/client";
import type { ContractDetail as Detail, Severity } from "../api/types";
import { Meter } from "../components/charts";
import ComparePanel from "../components/ComparePanel";
import CompliancePanel from "../components/CompliancePanel";
import PipelineStepper from "../components/PipelineStepper";
import SignPanel from "../components/SignPanel";
import {
  Button,
  Card,
  Chip,
  EmptyState,
  ErrorBox,
  Notice,
  PageLink,
  SEVERITY,
  SeverityBadge,
  Skeleton,
  StatusPill,
  Tabs,
  cx,
  formatDate,
  type Icon,
} from "../components/ui";

type Tab = "overview" | "risks" | "clauses" | "compare" | "compliance" | "obligations" | "sign";
const SEV_ORDER: Record<Severity, number> = { critical: 0, high: 1, medium: 2, low: 3 };
const TERM_ICON: Record<string, Icon> = {
  term_length: Clock,
  auto_renew: Repeat,
  notice_period: BellRing,
  liability_cap: Scale,
  payment_terms: Wallet,
  fees: Banknote,
  governing_law: Landmark,
  effective_date: CalendarCheck,
  expiry_date: CalendarX,
};

export default function ContractDetail() {
  const id = Number(useParams().id);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("overview");
  const [page, setPage] = useState(1);
  const [showDoc, setShowDoc] = useState(true);

  const q = useQuery({
    queryKey: ["contract", id],
    queryFn: () => api.getContract(id),
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return s === "processing" || s === "uploaded" ? 1200 : false;
    },
  });
  const reanalyze = useMutation({
    mutationFn: () => api.reanalyze(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["contract", id] });
      qc.invalidateQueries({ queryKey: ["contracts"] });
    },
  });
  const del = useMutation({
    mutationFn: () => api.deleteContract(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["contracts"] });
      navigate("/contracts");
    },
  });

  if (q.isLoading)
    return (
      <div className="space-y-4">
        <Skeleton className="h-40 rounded-xl" />
        <Skeleton className="h-12 rounded-xl" />
        <Skeleton className="h-96 rounded-xl" />
      </div>
    );
  if (q.error || !q.data) return <ErrorBox error={q.error ?? "Contract not found"} />;

  const c = q.data;
  const busy = c.status === "processing" || c.status === "uploaded";
  const goto = (p: number) => {
    setPage(p);
    setShowDoc(true);
  };
  const flagCounts = c.risk_flags.reduce<Record<string, number>>((m, f) => ({ ...m, [f.severity]: (m[f.severity] ?? 0) + 1 }), {});

  return (
    <div className="space-y-6">
      <Link to={c.is_mine ? "/contracts" : "/admin/contracts"} className="inline-flex items-center gap-1.5 text-sm text-ink-2 hover:text-ink">
        <ArrowLeft className="h-4 w-4" /> All contracts
      </Link>
      {!c.is_mine && (
        <Notice tone="info">
          Admin view — this contract belongs to <b>{c.owner?.name ?? "an unassigned user"}</b>
          {c.owner?.email ? ` (${c.owner.email})` : ""}.
        </Notice>
      )}

      {/* ---------- header ---------- */}
      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2" bodyClassName="p-6">
          <div className="flex flex-wrap items-start gap-4">
            <span className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-grad-a to-grad-b text-white shadow-pop">
              <FileText className="h-7 w-7" />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="truncate text-xl font-semibold tracking-tight">{c.filename}</h1>
                <StatusPill status={c.status} label={c.status === "done" ? "analyzed" : undefined} />
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {c.contract_type && (
                  <Chip icon={BookText}>
                    {c.contract_type}
                    {c.type_confidence ? <span className="text-muted"> · {Math.round(c.type_confidence * 100)}%</span> : null}
                  </Chip>
                )}
                {c.page_count && <Chip icon={FileText}>{c.page_count} pages</Chip>}
                {c.governing_law && <Chip icon={Landmark}>{c.governing_law} law</Chip>}
                {c.language && <Chip icon={Languages}>{c.language.toUpperCase()}</Chip>}
                {c.effective_date && <Chip icon={CalendarCheck}>From {formatDate(c.effective_date)}</Chip>}
                {c.expiry_date && <Chip icon={CalendarX}>To {formatDate(c.expiry_date)}</Chip>}
              </div>
              {!!c.parties?.length && (
                <div className="mt-4 flex flex-wrap items-center gap-2 text-sm">
                  <Users className="h-4 w-4 text-muted" />
                  {c.parties.map((p, i) => (
                    <span key={i} className="rounded-lg border border-line px-2.5 py-1">
                      <span className="font-medium">{p.name}</span>
                      {p.role && <span className="ml-1 text-xs text-muted">({p.role})</span>}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
          <div className="mt-5 flex flex-wrap gap-2 border-t border-line pt-4">
            {c.status === "done" && (
              <a href={api.reportUrl(id)} target="_blank" rel="noreferrer">
                <Button icon={FileText}>Open risk report</Button>
              </a>
            )}
            <Button variant="secondary" icon={RefreshCw} disabled={busy} loading={reanalyze.isPending} onClick={() => reanalyze.mutate()}>
              Re-analyze
            </Button>
            <Button variant="secondary" icon={showDoc ? EyeOff : Eye} onClick={() => setShowDoc((s) => !s)}>
              {showDoc ? "Hide document" : "Show document"}
            </Button>
            <Button
              variant="danger"
              icon={Trash2}
              className="ml-auto"
              onClick={() => confirm("Delete this contract and its analysis?") && del.mutate()}
            >
              Delete
            </Button>
          </div>
        </Card>

        <Card bodyClassName="p-6">
          <p className="text-sm font-medium text-ink-2">Overall risk score</p>
          {c.report ? (
            <>
              <div className="mt-2 flex items-end gap-3">
                <span className="text-5xl font-semibold tracking-tight">{c.report.risk_score}</span>
                <span className="mb-1.5 text-sm text-muted">/ 100</span>
                <span className="mb-1.5 ml-auto">
                  <SeverityBadge severity={c.report.risk_level} size="md" />
                </span>
              </div>
              <div className="mt-4">
                <Meter value={c.report.risk_score} fill={SEVERITY[c.report.risk_level].bar} label="Risk score" />
                <div className="mt-1.5 flex justify-between text-[11px] text-muted">
                  <span>Low</span>
                  <span>Medium</span>
                  <span>High</span>
                  <span>Critical</span>
                </div>
              </div>
              <ul className="mt-5 grid grid-cols-2 gap-2">
                {(["critical", "high", "medium", "low"] as Severity[]).map((s) => {
                  const S = SEVERITY[s];
                  const I = S.icon;
                  return (
                    <li key={s} className="flex items-center gap-2 rounded-lg border border-line px-3 py-2 text-sm">
                      <span className={cx("h-2 w-2 rounded-full", S.dot)} />
                      <I className="h-3.5 w-3.5 text-muted" aria-hidden />
                      <span className="text-ink-2">{S.label}</span>
                      <span className="tnum ml-auto font-semibold">{flagCounts[s] ?? 0}</span>
                    </li>
                  );
                })}
              </ul>
            </>
          ) : busy ? (
            <div className="mt-4 space-y-3">
              <Skeleton className="h-12 w-24" />
              <Skeleton className="h-2" />
            </div>
          ) : (
            <p className="mt-3 text-sm text-muted">Not available.</p>
          )}
        </Card>
      </div>

      {busy && (
        <Card title="Analyzing your contract" subtitle={`Stage: ${c.latest_job?.stage ?? "queued"}`} icon={Sparkles}>
          <PipelineStepper stage={c.latest_job?.stage} status={c.latest_job?.status} progress={c.latest_job?.progress ?? 0} />
        </Card>
      )}
      {c.status === "failed" && <ErrorBox error={c.latest_job?.error?.split("\n")[0] ?? "Analysis failed"} />}
      {!!c.warnings?.length && (
        <Notice>
          <ul className="space-y-1">
            {c.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </Notice>
      )}

      {c.status === "done" && (
        <>
          <KeyTerms c={c} goto={goto} />

          <div className={cx("grid gap-6", showDoc && "2xl:grid-cols-[minmax(0,1fr)_minmax(0,0.85fr)]")}>
            <div className="min-w-0 space-y-4">
              <Tabs<Tab>
                value={tab}
                onChange={setTab}
                tabs={[
                  { id: "overview", label: "Summary", icon: Sparkles },
                  { id: "risks", label: "Risks", icon: ShieldAlert, count: c.risk_flags.length },
                  { id: "clauses", label: "Clauses", icon: ListTree, count: c.clauses.length },
                  { id: "compare", label: "Compare", icon: GitCompareArrows },
                  { id: "compliance", label: "Compliance", icon: ShieldCheck },
                  { id: "obligations", label: "Obligations", icon: CalendarClock, count: c.obligations.length },
                  { id: "sign", label: "Sign & share", icon: FileSignature },
                ]}
              />
              <div key={tab} className="animate-fade-in">
                {tab === "overview" && <Overview c={c} />}
                {tab === "risks" && <Risks c={c} goto={goto} />}
                {tab === "clauses" && <Clauses c={c} goto={goto} />}
                {tab === "compare" && <ComparePanel contractId={id} goto={goto} />}
                {tab === "compliance" && <CompliancePanel contractId={id} goto={goto} />}
                {tab === "obligations" && <ObligationsTab c={c} goto={goto} />}
                {tab === "sign" && <SignPanel contractId={id} />}
              </div>
            </div>
            {showDoc && (
              <div className="min-w-0 2xl:sticky 2xl:top-20 2xl:self-start">
                <Card
                  title="Document"
                  subtitle={`Page ${page}${c.page_count ? ` of ${c.page_count}` : ""}`}
                  icon={FileText}
                  bodyClassName="p-2"
                  actions={
                    <a href={api.fileUrl(id)} target="_blank" rel="noreferrer" className="text-xs font-medium text-brand hover:underline">
                      Open in new tab
                    </a>
                  }
                >
                  <iframe
                    key={page}
                    title="Contract document"
                    src={`${api.fileUrl(id)}#page=${page}&view=FitH`}
                    className="h-[78vh] w-full rounded-lg bg-surface-2"
                  />
                </Card>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

type TabProps = { c: Detail; goto: (p: number) => void };

function KeyTerms({ c, goto }: TabProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-5">
      {c.terms.map((t) => {
        const I = TERM_ICON[t.key] ?? FileText;
        const missing = t.display.startsWith("Missing") || t.display === "Unlimited";
        const unset = t.display === "Not specified";
        return (
          <div
            key={t.id}
            title={t.raw_text ?? undefined}
            className={cx(
              "group animate-fade-in rounded-xl border bg-surface p-4 shadow-card transition hover:shadow-pop",
              missing ? "border-critical/40" : "border-line",
            )}
          >
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-xs font-medium text-ink-2">
                <I className={cx("h-4 w-4", missing ? "text-critical" : "text-brand")} />
                {t.label}
              </span>
              <PageLink page={t.page} onClick={goto} />
            </div>
            <p className={cx("mt-2 text-base font-semibold leading-snug", unset && "text-muted")}>
              {/^\d{4}-\d{2}-\d{2}$/.test(t.display) ? formatDate(t.display) : t.display}
            </p>
            {missing && (
              <p className="mt-1 flex items-center gap-1 text-xs text-ink-2">
                <ShieldAlert className="h-3.5 w-3.5 text-critical" /> Needs attention
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}

function Overview({ c }: { c: Detail }) {
  return (
    <div className="space-y-4">
      <Card title="Plain-language summary" subtitle="Explain this contract in simple terms" icon={Sparkles}>
        <p className="text-[15px] leading-relaxed">{c.report?.summary}</p>
        {!!c.report?.key_points?.length && (
          <ul className="mt-4 grid gap-2 sm:grid-cols-2">
            {c.report.key_points.map((p, i) => (
              <li key={i} className="flex gap-2 rounded-lg bg-surface-2 p-3 text-sm">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand" />
                {p}
              </li>
            ))}
          </ul>
        )}
        <p className="mt-4 flex items-center gap-1.5 text-xs text-muted">
          <Sparkles className="h-3.5 w-3.5" />
          {c.report?.llm_model ? `Written by local model ${c.report.llm_model}` : "Rule-based summary (start Ollama for an AI-written one)"} · not legal
          advice
        </p>
      </Card>
      {!!c.report?.negotiation?.length && (
        <Card title="Top negotiation points" icon={Handshake}>
          <ol className="space-y-2">
            {c.report.negotiation.slice(0, 3).map((n, i) => (
              <li key={i} className="flex gap-3 text-sm">
                <span className="tnum grid h-6 w-6 shrink-0 place-items-center rounded-full bg-brand-soft text-xs font-semibold text-brand">{i + 1}</span>
                <span className="pt-0.5">{n.suggestion}</span>
              </li>
            ))}
          </ol>
        </Card>
      )}
    </div>
  );
}

function Risks({ c, goto }: TabProps) {
  const [filter, setFilter] = useState<Severity | "all">("all");
  const flags = [...c.risk_flags]
    .sort((a, b) => SEV_ORDER[a.severity] - SEV_ORDER[b.severity])
    .filter((f) => filter === "all" || f.severity === filter);
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {(["all", "critical", "high", "medium", "low"] as const).map((s) => {
          const n = s === "all" ? c.risk_flags.length : c.risk_flags.filter((f) => f.severity === s).length;
          return (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={cx(
                "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ring-1 ring-inset transition",
                filter === s ? "bg-ink text-page ring-ink" : "bg-surface text-ink-2 ring-line hover:bg-surface-2",
              )}
            >
              {s !== "all" && <span className={cx("h-1.5 w-1.5 rounded-full", SEVERITY[s].dot)} />}
              {s === "all" ? "All" : SEVERITY[s].label}
              <span className="tnum opacity-70">{n}</span>
            </button>
          );
        })}
      </div>

      {flags.length === 0 ? (
        <Card>
          <EmptyState icon={ShieldCheck} title="No risks at this level" />
        </Card>
      ) : (
        <ul className="space-y-3">
          {flags.map((f) => (
            <li key={f.id} className="relative animate-fade-in overflow-hidden rounded-xl border border-line bg-surface p-4 pl-5 shadow-card">
              <span className={cx("absolute inset-y-0 left-0 w-1", SEVERITY[f.severity].bar)} aria-hidden />
              <div className="flex flex-wrap items-start gap-3">
                <SeverityBadge severity={f.severity} />
                <div className="min-w-0 flex-1">
                  <p className="font-medium">{f.message}</p>
                  {f.suggestion && (
                    <p className="mt-2 flex gap-2 rounded-lg bg-brand-soft/60 p-2.5 text-sm text-ink">
                      <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-brand" />
                      {f.suggestion}
                    </p>
                  )}
                  {f.evidence && (
                    <p className="mt-2 flex gap-2 text-xs italic text-ink-2">
                      <Quote className="h-3.5 w-3.5 shrink-0 text-muted" />
                      {f.evidence.slice(0, 300)}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className="rounded bg-surface-2 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted">
                    {f.source === "llm" ? "AI" : "Rule"}
                  </span>
                  <PageLink page={f.page} onClick={goto} />
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}

      <Card title="Negotiation suggestions" icon={Handshake}>
        {!c.report?.negotiation?.length ? (
          <EmptyState icon={Handshake} title="No suggestions" />
        ) : (
          <ol className="space-y-3">
            {c.report.negotiation.map((n, i) => (
              <li key={i} className="flex gap-3">
                <span className="tnum grid h-6 w-6 shrink-0 place-items-center rounded-full bg-brand-soft text-xs font-semibold text-brand">{i + 1}</span>
                <div className="min-w-0 text-sm">
                  <p>{n.suggestion}</p>
                  {n.standard_position && <p className="mt-0.5 text-xs text-muted">Market standard: {n.standard_position}</p>}
                </div>
                <span className="ml-auto">
                  <SeverityBadge severity={n.priority} />
                </span>
              </li>
            ))}
          </ol>
        )}
      </Card>
    </div>
  );
}

function Clauses({ c, goto }: TabProps) {
  const [open, setOpen] = useState<number | null>(null);
  if (!c.clauses.length)
    return (
      <Card>
        <EmptyState icon={ListTree} title="No clauses identified" />
      </Card>
    );
  return (
    <Card title="Extracted clauses" subtitle={`${c.clauses.length} clauses identified`} icon={ListTree} bodyClassName="p-0">
      <ul className="divide-y divide-line">
        {c.clauses.map((cl) => (
          <li key={cl.id}>
            <button className="flex w-full items-center gap-3 px-5 py-3 text-left hover:bg-surface-2" onClick={() => setOpen(open === cl.id ? null : cl.id)}>
              <ChevronDown className={cx("h-4 w-4 shrink-0 text-muted transition", open === cl.id && "rotate-180")} />
              <span className="min-w-0 flex-1">
                <span className="block text-sm font-medium capitalize">{cl.type.replace(/_/g, " ")}</span>
                <span className="block truncate text-xs text-muted">{cl.heading}</span>
              </span>
              {cl.needs_review && <StatusPill status="needs_review" />}
              <span className="hidden items-center gap-2 sm:flex" title="Extraction confidence">
                <span className="h-1.5 w-12 overflow-hidden rounded-full bg-track">
                  <span className="block h-full rounded-full bg-series" style={{ width: `${cl.confidence * 100}%` }} />
                </span>
                <span className="tnum w-8 text-xs text-ink-2">{Math.round(cl.confidence * 100)}%</span>
              </span>
              <span onClick={(e) => e.stopPropagation()}>
                <PageLink page={cl.page} onClick={goto} />
              </span>
            </button>
            {open === cl.id && (
              <div className="animate-fade-in px-5 pb-4">
                <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-lg bg-surface-2 p-4 font-sans text-sm leading-relaxed">{cl.text}</pre>
              </div>
            )}
          </li>
        ))}
      </ul>
    </Card>
  );
}

function ObligationsTab({ c, goto }: TabProps) {
  const dated = c.obligations.filter((o) => o.due_date).sort((a, b) => a.due_date!.localeCompare(b.due_date!));
  const ongoing = c.obligations.filter((o) => !o.due_date);
  if (!c.obligations.length)
    return (
      <Card>
        <EmptyState icon={CalendarClock} title="No obligations identified" />
      </Card>
    );
  return (
    <div className="space-y-4">
      {!!dated.length && (
        <Card title="Key dates" icon={CalendarClock}>
          <ol className="relative ml-2 border-l border-line">
            {dated.map((o) => (
              <li key={o.id} className="mb-5 ml-5 last:mb-0">
                <span
                  className={cx(
                    "absolute -left-[7px] mt-1 h-3.5 w-3.5 rounded-full border-2 border-surface",
                    o.kind === "renewal_notice" ? "bg-serious" : o.kind === "expiry" ? "bg-critical" : "bg-series",
                  )}
                />
                <p className="tnum text-sm font-semibold">{formatDate(o.due_date)}</p>
                <p className="mt-0.5 text-sm text-ink-2">{o.description}</p>
                <div className="mt-1 flex items-center gap-2">
                  <StatusPill status={o.status} label={o.kind.replace("_", " ")} />
                  <PageLink page={o.page} onClick={goto} />
                </div>
              </li>
            ))}
          </ol>
        </Card>
      )}
      {!!ongoing.length && (
        <Card title="Ongoing obligations" icon={ListTree} bodyClassName="p-0">
          <ul className="divide-y divide-line">
            {ongoing.map((o) => (
              <li key={o.id} className="flex items-start gap-3 px-5 py-3 text-sm">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand" />
                <span className="flex-1">{o.description}</span>
                <PageLink page={o.page} onClick={goto} />
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
