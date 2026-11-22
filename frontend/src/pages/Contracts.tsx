import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { FileStack, Filter, Search, UploadCloud } from "lucide-react";
import { api } from "../api/client";
import type { Severity } from "../api/types";
import { Button, Card, EmptyState, ErrorBox, PageHeader, Select, Skeleton } from "../components/ui";
import { ContractTable } from "./Dashboard";

const SORTS = {
  recent: "Most recent",
  risk: "Highest risk",
  expiry: "Expiring soonest",
  name: "Name A–Z",
} as const;

export default function Contracts() {
  const q = useQuery({
    queryKey: ["contracts"],
    queryFn: api.listContracts,
    refetchInterval: (qq) => (qq.state.data?.some((c) => c.status === "processing" || c.status === "uploaded") ? 2000 : false),
  });
  const [search, setSearch] = useState("");
  const [risk, setRisk] = useState<"" | Severity>("");
  const [type, setType] = useState("");
  const [sort, setSort] = useState<keyof typeof SORTS>("recent");

  const types = useMemo(() => [...new Set((q.data ?? []).map((c) => c.contract_type).filter(Boolean) as string[])].sort(), [q.data]);
  const rows = useMemo(() => {
    const s = search.trim().toLowerCase();
    const out = (q.data ?? []).filter(
      (c) =>
        (!s || [c.filename, c.contract_type, c.governing_law].some((v) => v?.toLowerCase().includes(s))) &&
        (!risk || c.risk_level === risk) &&
        (!type || c.contract_type === type),
    );
    const cmp: Record<keyof typeof SORTS, (a: (typeof out)[0], b: (typeof out)[0]) => number> = {
      recent: (a, b) => b.uploaded_at.localeCompare(a.uploaded_at),
      risk: (a, b) => (b.risk_score ?? -1) - (a.risk_score ?? -1),
      expiry: (a, b) => (a.expiry_date ?? "9999").localeCompare(b.expiry_date ?? "9999"),
      name: (a, b) => a.filename.localeCompare(b.filename),
    };
    return out.sort(cmp[sort]);
  }, [q.data, search, risk, type, sort]);

  return (
    <div>
      <PageHeader
        title="Contracts"
        description="Every contract you've uploaded, with its type, deadlines and risk."
        actions={
          <Link to="/upload">
            <Button icon={UploadCloud}>Upload contract</Button>
          </Link>
        }
      />
      <Card bodyClassName="p-0">
        <div className="flex flex-wrap items-center gap-3 border-b border-line p-4">
          <div className="relative min-w-[220px] flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Filter by name, type or law…" className="input pl-9" />
          </div>
          <Filter className="h-4 w-4 text-muted" aria-hidden />
          <Select value={type} onChange={(e) => setType(e.target.value)} aria-label="Contract type">
            <option value="">All types</option>
            {types.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </Select>
          <Select value={risk} onChange={(e) => setRisk(e.target.value as Severity | "")} aria-label="Risk level">
            <option value="">All risk levels</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </Select>
          <Select value={sort} onChange={(e) => setSort(e.target.value as keyof typeof SORTS)} aria-label="Sort">
            {Object.entries(SORTS).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </Select>
        </div>
        <ErrorBox error={q.error} />
        {q.isLoading ? (
          <div className="space-y-3 p-5">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-10" />
            ))}
          </div>
        ) : rows.length ? (
          <ContractTable rows={rows} />
        ) : (
          <EmptyState
            icon={FileStack}
            title={q.data?.length ? "No contracts match your filters" : "No contracts yet"}
            description={q.data?.length ? "Try clearing a filter." : "Upload a PDF to get started."}
          />
        )}
        {!!rows.length && <p className="border-t border-line px-5 py-3 text-xs text-muted">{rows.length} contract(s)</p>}
      </Card>
    </div>
  );
}
