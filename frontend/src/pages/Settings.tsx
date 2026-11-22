import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Brain, CheckCircle2, CircleDashed, Cpu, FileSignature, HardDrive, Link2, PenLine, PlugZap, ScanText, Unplug } from "lucide-react";
import { api } from "../api/client";
import { Button, Card, ErrorBox, Notice, PageHeader, Skeleton, cx, type Icon } from "../components/ui";
import { useAuth } from "../lib/auth";

function SystemRow({ icon: I, title, ok, value, hint }: { icon: Icon; title: string; ok: boolean; value: string; hint?: string | null }) {
  return (
    <li className="flex items-start gap-4 py-4 first:pt-0 last:pb-0">
      <span className={cx("grid h-10 w-10 shrink-0 place-items-center rounded-xl", ok ? "bg-good/10 text-good" : "bg-surface-2 text-muted")}>
        <I className="h-5 w-5" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium">{title}</p>
        <p className="text-sm text-ink-2">{value}</p>
        {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
      </div>
      <span className={cx("inline-flex items-center gap-1 text-xs font-medium", ok ? "text-ink" : "text-muted")}>
        {ok ? <CheckCircle2 className="h-4 w-4 text-good" /> : <CircleDashed className="h-4 w-4" />}
        {ok ? "Ready" : "Not available"}
      </span>
    </li>
  );
}

const INTEGRATION_ICON: Record<string, Icon> = { gdrive: HardDrive, docusign: FileSignature, dropbox_sign: PenLine, adobe_sign: FileSignature };

export default function Settings() {
  const qc = useQueryClient();
  const { isAdmin } = useAuth();
  const [params] = useSearchParams();
  const health = useQuery({ queryKey: ["health"], queryFn: api.health });
  const integrations = useQuery({ queryKey: ["integrations"], queryFn: api.integrations });

  const connect = useMutation({
    mutationFn: api.connect,
    onSuccess: (r) => {
      window.location.href = r.authorize_url;
    },
  });
  const disconnect = useMutation({
    mutationFn: api.disconnect,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["integrations"] }),
  });

  const h = health.data;
  return (
    <div>
      <PageHeader title="Settings" description="Local AI engine status and optional integrations." />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card title="Local AI engine" subtitle="Everything runs on this machine — free and private" icon={Cpu}>
          <ErrorBox error={health.error} />
          {!h ? (
            <div className="space-y-4">
              <Skeleton className="h-12" />
              <Skeleton className="h-12" />
              <Skeleton className="h-12" />
            </div>
          ) : (
            <ul className="divide-y divide-line">
              <SystemRow
                icon={Brain}
                title="Language model (Ollama)"
                ok={h.llm.ok}
                value={`${h.llm.provider} · ${h.llm.model}`}
                hint={h.llm.ok ? "Classification, risk review, summaries and suggestions use this model." : h.llm.hint ?? h.llm.error}
              />
              <SystemRow
                icon={ScanText}
                title="OCR for scanned PDFs (Tesseract)"
                ok={h.ocr.tesseract}
                value={h.ocr.tesseract ? `Languages: ${h.ocr.languages}` : "Not installed"}
                hint={h.ocr.tesseract ? null : "Install the UB Mannheim build and set TESSERACT_CMD in .env."}
              />
              <SystemRow
                icon={PenLine}
                title="Handwriting recognition (TrOCR)"
                ok={h.handwriting.trocr}
                value={h.handwriting.trocr ? "Available" : "Optional extra"}
                hint={h.handwriting.trocr ? null : 'Install with: pip install -e ".[vision]"'}
              />
            </ul>
          )}
        </Card>

        <Card title="Integrations" subtitle="Optional · free sandbox / test modes only" icon={PlugZap}>
          <div className="space-y-3">
            {params.get("connected") && <Notice tone="good">Connected {params.get("connected")}.</Notice>}
            {params.get("error") && <ErrorBox error={params.get("error")} />}
            <ErrorBox error={connect.error ?? disconnect.error} />
          </div>
          <ul className="mt-2 grid gap-3 sm:grid-cols-2">
            {integrations.data?.map((i) => {
              const I = INTEGRATION_ICON[i.key] ?? Link2;
              return (
                <li key={i.key} className="flex flex-col rounded-xl border border-line p-4">
                  <div className="flex items-center gap-3">
                    <span className={cx("grid h-10 w-10 place-items-center rounded-xl", i.connected ? "bg-good/10 text-good" : "bg-surface-2 text-ink-2")}>
                      <I className="h-5 w-5" />
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{i.label}</p>
                      <p className="flex items-center gap-1.5 text-xs text-muted">
                        <span className={cx("h-1.5 w-1.5 rounded-full", i.connected ? "bg-good" : i.configured ? "bg-warning" : "bg-muted")} />
                        {!i.configured ? "Disabled in .env" : i.connected ? "Connected" : "Not connected"}
                      </p>
                    </div>
                  </div>
                  <div className="mt-4">
                    {isAdmin && i.configured && i.oauth && !i.connected && (
                      <Button size="sm" icon={Link2} loading={connect.isPending && connect.variables === i.key} onClick={() => connect.mutate(i.key)}>
                        Connect
                      </Button>
                    )}
                    {isAdmin && i.configured && i.oauth && i.connected && (
                      <Button size="sm" variant="secondary" icon={Unplug} onClick={() => disconnect.mutate(i.key)}>
                        Disconnect
                      </Button>
                    )}
                    {!i.configured && isAdmin && <p className="text-xs text-ink-2">Set ENABLE_{i.key.toUpperCase()}=true and credentials in .env.</p>}
                  </div>
                </li>
              );
            })}
          </ul>
        </Card>
      </div>
    </div>
  );
}
