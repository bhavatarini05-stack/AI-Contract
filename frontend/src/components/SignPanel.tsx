import { useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CloudUpload, FileSignature, HardDrive, Plus, RefreshCw, Send, Trash2 } from "lucide-react";
import { api } from "../api/client";
import { Button, Card, EmptyState, ErrorBox, Notice, Select, StatusPill, formatDate } from "./ui";

export default function SignPanel({ contractId }: { contractId: number }) {
  const qc = useQueryClient();
  const integrations = useQuery({ queryKey: ["integrations"], queryFn: api.integrations });
  const signers = integrations.data?.filter((i) => i.kind === "signature" && i.connected) ?? [];
  const drive = integrations.data?.find((i) => i.key === "gdrive" && i.connected);
  const requests = useQuery({ queryKey: ["sigreq", contractId], queryFn: () => api.signatureRequests(contractId) });

  const [provider, setProvider] = useState("");
  const [rows, setRows] = useState([{ name: "", email: "" }]);
  const chosen = provider || signers[0]?.key || "";
  const valid = rows.filter((r) => r.name && /\S+@\S+\.\S+/.test(r.email));

  const send = useMutation({
    mutationFn: () => api.sendForSignature(chosen, contractId, valid),
    onSuccess: () => {
      setRows([{ name: "", email: "" }]);
      qc.invalidateQueries({ queryKey: ["sigreq", contractId] });
    },
  });
  const refresh = useMutation({
    mutationFn: api.refreshSignature,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sigreq", contractId] }),
  });
  const exportDrive = useMutation({ mutationFn: () => api.driveExport(contractId) });

  return (
    <div className="space-y-4">
      <Card title="Send for e-signature" subtitle="DocuSign · Dropbox Sign · Adobe Sign (sandbox modes)" icon={FileSignature}>
        {signers.length === 0 ? (
          <EmptyState
            icon={FileSignature}
            title="No e-signature provider connected"
            description="Enable DocuSign, Dropbox Sign or Adobe Sign (free developer sandboxes) in .env, then connect them in Settings."
            action={
              <Link to="/settings" className="text-sm font-medium text-brand hover:underline">
                Open Settings
              </Link>
            }
          />
        ) : (
          <div className="space-y-4">
            <div>
              <label className="label">Provider</label>
              <Select value={chosen} onChange={(e) => setProvider(e.target.value)}>
                {signers.map((s) => (
                  <option key={s.key} value={s.key}>
                    {s.label}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-2">
              <label className="label">Signers (signing order)</label>
              {rows.map((r, i) => (
                <div key={i} className="flex items-center gap-2">
                  <span className="tnum grid h-7 w-7 shrink-0 place-items-center rounded-full bg-surface-2 text-xs font-semibold text-ink-2">{i + 1}</span>
                  <input
                    placeholder="Full name"
                    value={r.name}
                    onChange={(e) => setRows(rows.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))}
                    className="input"
                  />
                  <input
                    placeholder="email@example.com"
                    type="email"
                    value={r.email}
                    onChange={(e) => setRows(rows.map((x, j) => (j === i ? { ...x, email: e.target.value } : x)))}
                    className="input"
                  />
                  {rows.length > 1 && (
                    <button onClick={() => setRows(rows.filter((_, j) => j !== i))} className="rounded-md p-2 text-muted hover:bg-surface-2 hover:text-critical" aria-label="Remove signer">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <Button variant="secondary" icon={Plus} onClick={() => setRows([...rows, { name: "", email: "" }])}>
                Add signer
              </Button>
              <Button icon={Send} loading={send.isPending} disabled={!valid.length} onClick={() => send.mutate()}>
                Send for signature
              </Button>
            </div>
            <ErrorBox error={send.error} />
          </div>
        )}
      </Card>

      <Card title="Signature requests" icon={Send} bodyClassName="p-0">
        <div className="px-5 pt-4">
          <ErrorBox error={refresh.error} />
        </div>
        {requests.data?.length ? (
          <ul className="divide-y divide-line">
            {requests.data.map((r) => (
              <li key={r.id} className="flex items-center gap-3 px-5 py-3 text-sm">
                <span className="min-w-0 flex-1">
                  <span className="block font-medium capitalize">{r.provider.replace("_", " ")}</span>
                  <span className="block truncate text-xs text-muted">
                    {r.signers.map((s) => s.email).join(", ")} · {formatDate(r.created_at)}
                  </span>
                </span>
                <StatusPill status={r.status} />
                <Button size="sm" variant="secondary" icon={RefreshCw} loading={refresh.isPending && refresh.variables === r.id} onClick={() => refresh.mutate(r.id)}>
                  Refresh
                </Button>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState icon={Send} title="No signature requests yet" />
        )}
        {refresh.data?.imported_contract_id && (
          <div className="p-4">
            <Notice tone="good">
              Signed copy imported and re-analyzed —{" "}
              <Link className="font-medium underline" to={`/contracts/${refresh.data.imported_contract_id}`}>
                open it
              </Link>
              .
            </Notice>
          </div>
        )}
      </Card>

      <Card title="Google Drive" icon={HardDrive}>
        {drive ? (
          <div className="space-y-3">
            <Button variant="secondary" icon={CloudUpload} loading={exportDrive.isPending} onClick={() => exportDrive.mutate()}>
              Save risk report to Drive
            </Button>
            {exportDrive.data && <Notice tone="good">Saved as “{exportDrive.data.name}”.</Notice>}
            <ErrorBox error={exportDrive.error} />
          </div>
        ) : (
          <p className="text-sm text-ink-2">
            Connect Google Drive in{" "}
            <Link to="/settings" className="font-medium text-brand hover:underline">
              Settings
            </Link>{" "}
            to save reports there.
          </p>
        )}
      </Card>
    </div>
  );
}
