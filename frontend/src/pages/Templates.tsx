import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, FilePlus2, ScrollText, Trash2, Upload } from "lucide-react";
import { api } from "../api/client";
import { Button, Card, EmptyState, ErrorBox, Notice, PageHeader, Skeleton, cx } from "../components/ui";
import { useAuth } from "../lib/auth";

export default function Templates() {
  const qc = useQueryClient();
  const { isAdmin } = useAuth();
  const list = useQuery({ queryKey: ["templates"], queryFn: api.listTemplates });
  const [name, setName] = useState("");
  const [content, setContent] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [mode, setMode] = useState<"paste" | "upload">("paste");
  const [view, setView] = useState<number | null>(null);

  const done = () => {
    qc.invalidateQueries({ queryKey: ["templates"] });
    setName("");
    setContent("");
    setFile(null);
  };
  const create = useMutation({
    mutationFn: () => (mode === "upload" && file ? api.uploadTemplate(name, file) : api.createTemplate({ name, content })),
    onSuccess: done,
  });
  const del = useMutation({ mutationFn: api.deleteTemplate, onSuccess: done });

  return (
    <div>
      <PageHeader title="Standard templates" description="Your company's preferred contract language — contracts are compared against these." />
      <div className="grid gap-6 lg:grid-cols-5">
        <Card className={isAdmin ? "lg:col-span-3" : "lg:col-span-5"} title="Templates" icon={ScrollText} bodyClassName="p-0">
          <div className="px-5 pt-4">
            <ErrorBox error={list.error ?? del.error} />
          </div>
          {list.isLoading ? (
            <div className="space-y-3 p-5">
              <Skeleton className="h-12" />
              <Skeleton className="h-12" />
            </div>
          ) : !list.data?.length ? (
            <EmptyState icon={ScrollText} title="No templates yet" description="Add one on the right." />
          ) : (
            <ul className="divide-y divide-line">
              {list.data.map((t) => (
                <li key={t.id}>
                  <div className="flex items-center gap-3 px-5 py-3">
                    <button className="flex min-w-0 flex-1 items-center gap-3 text-left" onClick={() => setView(view === t.id ? null : t.id)}>
                      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-brand-soft text-brand">
                        <ScrollText className="h-4 w-4" />
                      </span>
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-medium">{t.name}</span>
                        <span className="block text-xs text-muted">
                          {t.contract_type ?? "Any type"} · {t.content.split(/\s+/).length.toLocaleString()} words
                        </span>
                      </span>
                      <ChevronDown className={cx("ml-auto h-4 w-4 text-muted transition", view === t.id && "rotate-180")} />
                    </button>
                    {isAdmin && (
                      <Button size="sm" variant="danger" icon={Trash2} onClick={() => confirm(`Delete template "${t.name}"?`) && del.mutate(t.id)}>
                        Delete
                      </Button>
                    )}
                  </div>
                  {view === t.id && (
                    <pre className="mx-5 mb-4 max-h-96 animate-fade-in overflow-auto whitespace-pre-wrap rounded-lg bg-surface-2 p-4 font-sans text-sm leading-relaxed">
                      {t.content}
                    </pre>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Card>

        {!isAdmin && (
          <div className="lg:col-span-5">
            <Notice tone="info">Templates are managed by your administrator. You can compare any contract against them from its Compare tab.</Notice>
          </div>
        )}
        {isAdmin && (
        <Card className="lg:col-span-2" title="Add template" icon={FilePlus2}>
          <div className="space-y-4">
            <div>
              <label className="label">Name</label>
              <input placeholder="e.g. Standard MSA 2026" value={name} onChange={(e) => setName(e.target.value)} className="input" />
            </div>
            <div className="flex rounded-lg bg-surface-2 p-1 text-sm">
              {(["paste", "upload"] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={cx("flex-1 rounded-md py-1.5 capitalize transition", mode === m ? "bg-surface font-medium shadow-card" : "text-ink-2")}
                >
                  {m === "paste" ? "Paste text" : "Upload file"}
                </button>
              ))}
            </div>
            {mode === "upload" ? (
              <label className="flex cursor-pointer flex-col items-center rounded-xl border-2 border-dashed border-line p-6 text-center text-sm hover:border-brand/50">
                <Upload className="mb-2 h-6 w-6 text-muted" />
                {file ? <span className="font-medium">{file.name}</span> : <span className="text-ink-2">Choose a PDF, TXT or MD file</span>}
                <input type="file" accept=".pdf,.txt,.md" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
              </label>
            ) : (
              <div>
                <label className="label">Template text</label>
                <textarea
                  placeholder={"1. Term\nThe initial term shall be twelve (12) months…\n\n2. Limitation of Liability\n…"}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  rows={12}
                  className="input font-mono text-xs"
                />
                <p className="mt-1 text-xs text-muted">Use numbered headings so clauses can be matched.</p>
              </div>
            )}
            <Button
              icon={FilePlus2}
              className="w-full"
              loading={create.isPending}
              disabled={!name || (mode === "upload" ? !file : !content)}
              onClick={() => create.mutate()}
            >
              Save template
            </Button>
            <ErrorBox error={create.error} />
          </div>
        </Card>
        )}
      </div>
    </div>
  );
}
