import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowRightLeft, ChevronDown, GitCompareArrows, ScrollText, TriangleAlert } from "lucide-react";
import { api } from "../api/client";
import { Card, EmptyState, ErrorBox, PageLink, Select, Skeleton, StatusPill, cx } from "./ui";

export default function ComparePanel({ contractId, goto }: { contractId: number; goto: (p: number) => void }) {
  const templates = useQuery({ queryKey: ["templates"], queryFn: api.listTemplates });
  const [templateId, setTemplateId] = useState<number | null>(null);
  const tid = templateId ?? templates.data?.[0]?.id ?? null;
  const result = useQuery({
    queryKey: ["compare", contractId, tid],
    queryFn: () => api.compare(contractId, tid!),
    enabled: tid !== null,
  });
  const [open, setOpen] = useState<string | null>(null);

  if (templates.data?.length === 0)
    return (
      <Card>
        <EmptyState
          icon={ScrollText}
          title="No templates yet"
          description="Add your company's standard template to compare against."
          action={
            <Link to="/templates" className="text-sm font-medium text-brand hover:underline">
              Go to Templates
            </Link>
          }
        />
      </Card>
    );

  const r = result.data;
  return (
    <div className="space-y-4">
      <Card
        title="Compare with standard template"
        subtitle="Show differences between this contract and our standard template"
        icon={GitCompareArrows}
        actions={
          <Select value={tid ?? ""} onChange={(e) => setTemplateId(Number(e.target.value))} aria-label="Template">
            {templates.data?.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </Select>
        }
      >
        <ErrorBox error={result.error} />
        {result.isFetching && !r && <Skeleton className="h-40" />}
        {r && (
          <>
            <div className="mb-5 grid grid-cols-2 gap-2 sm:grid-cols-4">
              {(["same", "changed", "missing", "added"] as const).map((k) => (
                <div key={k} className="rounded-lg border border-line p-3">
                  <StatusPill status={k} />
                  <p className="tnum mt-1.5 text-2xl font-semibold">{r.counts[k]}</p>
                  <p className="text-[11px] text-muted">
                    {k === "missing" ? "in template, not here" : k === "added" ? "here, not in template" : `clauses ${k}`}
                  </p>
                </div>
              ))}
            </div>
            <div className="overflow-x-auto rounded-lg border border-line">
              <table className="w-full text-sm">
                <thead className="bg-surface-2 text-left text-[11px] font-semibold uppercase tracking-wider text-muted">
                  <tr>
                    <th className="px-4 py-2.5">Key term</th>
                    <th className="px-4 py-2.5">This contract</th>
                    <th className="px-4 py-2.5">Standard template</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {r.terms.map((t) => (
                    <tr key={t.key} className={t.differs ? "bg-warning/5" : ""}>
                      <td className="px-4 py-2.5 font-medium text-ink-2">
                        <span className="flex items-center gap-1.5">
                          {t.differs && <TriangleAlert className="h-3.5 w-3.5 text-warning" aria-label="differs" />}
                          {t.label}
                        </span>
                      </td>
                      <td className={cx("px-4 py-2.5", t.differs && "font-semibold")}>{t.contract}</td>
                      <td className="px-4 py-2.5 text-ink-2">{t.template}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </Card>

      {r && (
        <Card title="Clause-by-clause differences" icon={ArrowRightLeft} bodyClassName="p-0">
          <ul className="divide-y divide-line">
            {r.clauses.map((cl) => (
              <li key={cl.clause_type}>
                <button
                  className="flex w-full items-center gap-3 px-5 py-3 text-left hover:bg-surface-2"
                  onClick={() => setOpen(open === cl.clause_type ? null : cl.clause_type)}
                >
                  <ChevronDown className={cx("h-4 w-4 shrink-0 text-muted transition", open === cl.clause_type && "rotate-180")} />
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-medium">{cl.label}</span>
                    {cl.explanation && <span className="block text-xs text-ink-2">{cl.explanation}</span>}
                  </span>
                  {cl.less_favourable && (
                    <span className="rounded-full bg-critical/10 px-2 py-0.5 text-[11px] font-medium text-ink ring-1 ring-inset ring-critical/30">
                      less favourable
                    </span>
                  )}
                  {cl.status === "changed" && (
                    <span className="tnum hidden text-xs text-muted sm:inline">{Math.round(cl.similarity * 100)}% similar</span>
                  )}
                  <StatusPill status={cl.status} />
                  <span onClick={(e) => e.stopPropagation()}>
                    <PageLink page={cl.page} onClick={goto} />
                  </span>
                </button>
                {open === cl.clause_type && cl.diff.length > 0 && (
                  <div className="animate-fade-in px-5 pb-4">
                    <div className="space-y-1 rounded-lg border border-line bg-surface-2 p-3 font-mono text-xs leading-relaxed">
                      {cl.diff.map((d, i) => (
                        <p
                          key={i}
                          className={cx(
                            "rounded px-2 py-0.5",
                            d.op === "insert" && "bg-good/15",
                            d.op === "delete" && "bg-critical/10 line-through decoration-critical/50",
                            d.op === "equal" && "text-ink-2",
                          )}
                        >
                          <span className="mr-2 select-none font-bold">{d.op === "insert" ? "+" : d.op === "delete" ? "−" : " "}</span>
                          {d.text}
                        </p>
                      ))}
                    </div>
                    <p className="mt-2 text-[11px] text-muted">− only in template · + only in this contract</p>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
  );
}
