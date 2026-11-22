import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, CircleHelp, Quote, ShieldCheck, XCircle } from "lucide-react";
import { api } from "../api/client";
import { Meter } from "./charts";
import { Card, EmptyState, ErrorBox, PageLink, Select, SeverityBadge, Skeleton, StatusPill, cx } from "./ui";

const VERDICT = {
  pass: { icon: CheckCircle2, color: "text-good", label: "Pass" },
  fail: { icon: XCircle, color: "text-critical", label: "Fail" },
  unclear: { icon: CircleHelp, color: "text-warning", label: "Needs review" },
};

export default function CompliancePanel({ contractId, goto }: { contractId: number; goto: (p: number) => void }) {
  const policies = useQuery({ queryKey: ["policies"], queryFn: api.listPolicies });
  const [policyId, setPolicyId] = useState<number | null>(null);
  const pid = policyId ?? policies.data?.[0]?.id ?? null;
  const result = useQuery({
    queryKey: ["compliance", contractId, pid],
    queryFn: () => api.compliance(contractId, pid!),
    enabled: pid !== null,
  });

  if (policies.data?.length === 0)
    return (
      <Card>
        <EmptyState
          icon={ShieldCheck}
          title="No policies yet"
          action={
            <Link to="/policies" className="text-sm font-medium text-brand hover:underline">
              Create a policy
            </Link>
          }
        />
      </Card>
    );

  const r = result.data;
  const total = r ? r.results.length : 0;
  return (
    <Card
      title="Policy compliance"
      subtitle="Does this contract comply with our policy?"
      icon={ShieldCheck}
      actions={
        <Select value={pid ?? ""} onChange={(e) => setPolicyId(Number(e.target.value))} aria-label="Policy">
          {policies.data?.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </Select>
      }
    >
      <ErrorBox error={result.error} />
      {result.isFetching && !r && <Skeleton className="h-40" />}
      {r && (
        <>
          <div className="mb-5 flex flex-wrap items-center gap-4 rounded-xl bg-surface-2 p-4">
            <div>
              <p className="text-xs text-muted">Result</p>
              <div className="mt-1">
                <StatusPill status={r.overall} />
              </div>
            </div>
            <div className="min-w-[200px] flex-1">
              <div className="mb-1.5 flex justify-between text-xs text-ink-2">
                <span>
                  <b className="tnum text-ink">{r.passed}</b> of {total} requirements met
                </span>
                <span className="tnum">
                  {r.failed} failed · {r.unclear} to review
                </span>
              </div>
              <Meter value={r.passed} max={Math.max(total, 1)} fill="bg-good" label="Requirements met" />
            </div>
          </div>
          <ul className="space-y-2.5">
            {r.results.map((x) => {
              const V = VERDICT[x.verdict];
              return (
                <li key={x.id} className="rounded-xl border border-line p-4">
                  <div className="flex items-start gap-3">
                    <V.icon className={cx("mt-0.5 h-5 w-5 shrink-0", V.color)} aria-label={V.label} />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium">{x.requirement}</p>
                      <p className="mt-0.5 text-sm text-ink-2">
                        <span className="font-medium text-ink">{V.label}:</span> {x.explanation}
                      </p>
                      {x.evidence && (
                        <p className="mt-2 flex gap-2 text-xs italic text-ink-2">
                          <Quote className="h-3.5 w-3.5 shrink-0 text-muted" />
                          {x.evidence}
                        </p>
                      )}
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1.5">
                      <SeverityBadge severity={x.severity} />
                      <PageLink page={x.page} onClick={goto} />
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </Card>
  );
}
