import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Code2, Pencil, Plus, ShieldCheck, Trash2 } from "lucide-react";
import { api } from "../api/client";
import type { Policy, PolicyRule } from "../api/types";
import { Button, Card, EmptyState, ErrorBox, Notice, PageHeader, SeverityBadge, Skeleton, cx } from "../components/ui";
import { useAuth } from "../lib/auth";

const EXAMPLE: PolicyRule[] = [
  {
    id: "breach_notice",
    requirement: "Vendor must notify us of a data breach within 72 hours.",
    clause_types: ["data_protection"],
    must_include: ["breach", "72 hours|without undue delay"],
    severity: "high",
  },
];

export default function Policies() {
  const qc = useQueryClient();
  const { isAdmin } = useAuth();
  const list = useQuery({ queryKey: ["policies"], queryFn: api.listPolicies });
  const [editing, setEditing] = useState<Policy | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [rulesText, setRulesText] = useState(JSON.stringify(EXAMPLE, null, 2));
  const [parseError, setParseError] = useState<string | null>(null);

  useEffect(() => {
    if (editing) {
      setName(editing.name);
      setDescription(editing.description ?? "");
      setRulesText(JSON.stringify(editing.rules, null, 2));
    }
  }, [editing]);

  const reset = () => {
    setEditing(null);
    setName("");
    setDescription("");
    setRulesText(JSON.stringify(EXAMPLE, null, 2));
    setParseError(null);
    qc.invalidateQueries({ queryKey: ["policies"] });
  };

  const save = useMutation({
    mutationFn: () => {
      const rules = JSON.parse(rulesText) as PolicyRule[];
      const body = { name, description, rules };
      return editing ? api.updatePolicy(editing.id, body) : api.createPolicy(body);
    },
    onSuccess: reset,
  });
  const del = useMutation({ mutationFn: api.deletePolicy, onSuccess: reset });

  const onSave = () => {
    try {
      const parsed = JSON.parse(rulesText);
      if (!Array.isArray(parsed)) throw new Error("Rules must be a JSON array");
      setParseError(null);
      save.mutate();
    } catch (e) {
      setParseError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <div>
      <PageHeader title="Compliance policies" description="Internal rules every contract is checked against — e.g. your data privacy policy." />
      <div className="grid gap-6 lg:grid-cols-5">
        <div className={cx("space-y-4", isAdmin ? "lg:col-span-3" : "lg:col-span-5")}>
          {!isAdmin && <Notice tone="info">Policies are managed by your administrator. Run a check from any contract's Compliance tab.</Notice>}
          <ErrorBox error={list.error ?? del.error} />
          {list.isLoading ? (
            <Skeleton className="h-48 rounded-xl" />
          ) : !list.data?.length ? (
            <Card>
              <EmptyState icon={ShieldCheck} title="No policies yet" description="Create one on the right." />
            </Card>
          ) : (
            list.data.map((p) => (
              <Card
                key={p.id}
                title={p.name}
                subtitle={`${p.rules.length} requirement${p.rules.length === 1 ? "" : "s"}`}
                icon={ShieldCheck}
                className={cx(editing?.id === p.id && "ring-2 ring-brand/40")}
                actions={
                  isAdmin && <>
                    <Button size="sm" variant="secondary" icon={Pencil} onClick={() => setEditing(p)}>
                      Edit
                    </Button>
                    <Button size="sm" variant="danger" icon={Trash2} onClick={() => confirm(`Delete policy "${p.name}"?`) && del.mutate(p.id)}>
                      Delete
                    </Button>
                  </>
                }
              >
                {p.description && <p className="mb-3 text-sm text-ink-2">{p.description}</p>}
                <ul className="space-y-2">
                  {p.rules.map((r) => (
                    <li key={r.id} className="flex items-start gap-3 rounded-lg bg-surface-2 p-3 text-sm">
                      <SeverityBadge severity={r.severity ?? "medium"} />
                      <span className="flex-1">{r.requirement}</span>
                      <span className="hidden rounded bg-surface px-1.5 py-0.5 text-[10px] font-medium uppercase text-muted sm:inline">
                        {r.must_include?.length || r.must_not_include?.length ? "Rule" : "AI check"}
                      </span>
                    </li>
                  ))}
                </ul>
              </Card>
            ))
          )}
        </div>

        {isAdmin && (
        <Card
          className="self-start lg:col-span-2"
          title={editing ? `Edit “${editing.name}”` : "New policy"}
          icon={editing ? Pencil : Plus}
          actions={
            editing && (
              <Button size="sm" variant="ghost" onClick={reset}>
                Cancel
              </Button>
            )
          }
        >
          <div className="space-y-4">
            <div>
              <label className="label">Name</label>
              <input placeholder="e.g. Information Security Policy" value={name} onChange={(e) => setName(e.target.value)} className="input" />
            </div>
            <div>
              <label className="label">Description</label>
              <input placeholder="Optional" value={description} onChange={(e) => setDescription(e.target.value)} className="input" />
            </div>
            <div>
              <label className="label flex items-center gap-1.5">
                <Code2 className="h-3.5 w-3.5" /> Rules (JSON)
              </label>
              <textarea value={rulesText} onChange={(e) => setRulesText(e.target.value)} rows={16} spellCheck={false} className="input font-mono text-xs leading-relaxed" />
              <p className="mt-1.5 text-xs text-muted">
                Each rule: <code>id</code>, <code>requirement</code>, optional <code>clause_types</code>, <code>must_include</code> /{" "}
                <code>must_not_include</code> (regex lists) and <code>severity</code>. Rules without regexes are judged by the local LLM.
              </p>
            </div>
            <Button className="w-full" icon={editing ? Pencil : Plus} loading={save.isPending} disabled={!name} onClick={onSave}>
              {editing ? "Update policy" : "Create policy"}
            </Button>
            <ErrorBox error={parseError ?? save.error} />
          </div>
        </Card>
        )}
      </div>
    </div>
  );
}
