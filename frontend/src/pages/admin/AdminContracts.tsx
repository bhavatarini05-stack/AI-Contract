import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { FolderKanban, Search } from "lucide-react";
import { api } from "../../api/client";
import type { Severity } from "../../api/types";
import { Avatar } from "../../components/Layout";
import { Card, EmptyState, ErrorBox, PageHeader, RiskScore, Select, Skeleton, StatusPill, formatDate } from "../../components/ui";

export default function AdminContracts() {
  const q = useQuery({ queryKey: ["admin-contracts"], queryFn: api.adminContracts, refetchInterval: 10_000 });
  const [search, setSearch] = useState("");
  const [owner, setOwner] = useState("");
  const [risk, setRisk] = useState<"" | Severity>("");

  const owners = useMemo(() => [...new Set((q.data ?? []).map((c) => c.owner_email).filter(Boolean) as string[])].sort(), [q.data]);
  const rows = useMemo(() => {
    const s = search.trim().toLowerCase();
    return (q.data ?? []).filter(
      (c) =>
        (!s || [c.filename, c.contract_type, c.owner_name].some((v) => v?.toLowerCase().includes(s))) &&
        (!owner || c.owner_email === owner) &&
        (!risk || c.risk_level === risk),
    );
  }, [q.data, search, owner, risk]);

  return (
    <div>
      <PageHeader title="All contracts" description="Every contract in the organisation, with its owner." />
      <Card bodyClassName="p-0">
        <div className="flex flex-wrap items-center gap-3 border-b border-line p-4">
          <div className="relative min-w-[220px] flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input className="input pl-9" placeholder="Search contracts or owners…" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <Select value={owner} onChange={(e) => setOwner(e.target.value)} aria-label="Owner">
            <option value="">All owners</option>
            {owners.map((o) => (
              <option key={o}>{o}</option>
            ))}
          </Select>
          <Select value={risk} onChange={(e) => setRisk(e.target.value as Severity | "")} aria-label="Risk level">
            <option value="">All risk levels</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </Select>
        </div>
        <ErrorBox error={q.error} />
        {q.isLoading ? (
          <div className="space-y-3 p-5">
            <Skeleton className="h-10" />
            <Skeleton className="h-10" />
          </div>
        ) : !rows.length ? (
          <EmptyState icon={FolderKanban} title="No contracts found" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-[11px] font-semibold uppercase tracking-wider text-muted">
                  <th className="px-5 py-3">Contract</th>
                  <th className="px-3 py-3">Owner</th>
                  <th className="px-3 py-3">Type</th>
                  <th className="px-3 py-3">Expires</th>
                  <th className="px-3 py-3">Risk</th>
                  <th className="px-5 py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {rows.map((c) => (
                  <tr key={c.id} className="transition hover:bg-surface-2">
                    <td className="max-w-[260px] px-5 py-3">
                      <Link to={`/contracts/${c.id}`} className="block truncate font-medium hover:text-brand">
                        {c.filename}
                      </Link>
                      <span className="text-xs text-muted">Uploaded {formatDate(c.uploaded_at)}</span>
                    </td>
                    <td className="px-3 py-3">
                      {c.owner_name ? (
                        <div className="flex items-center gap-2">
                          <Avatar name={c.owner_name} size="sm" />
                          <div className="min-w-0">
                            <p className="truncate font-medium">{c.owner_name}</p>
                            <p className="truncate text-xs text-muted">{c.owner_email}</p>
                          </div>
                        </div>
                      ) : (
                        <span className="text-muted">Unassigned</span>
                      )}
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 text-ink-2">{c.contract_type ?? "—"}</td>
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
        )}
        {!!rows.length && <p className="border-t border-line px-5 py-3 text-xs text-muted">{rows.length} contract(s)</p>}
      </Card>
    </div>
  );
}
