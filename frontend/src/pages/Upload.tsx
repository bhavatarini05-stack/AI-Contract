import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { CloudDownload, FileText, HardDrive, Languages, Lock, ScanText, UploadCloud, X } from "lucide-react";
import { api } from "../api/client";
import PipelineStepper from "../components/PipelineStepper";
import { Button, Card, EmptyState, ErrorBox, PageHeader, cx, formatDate } from "../components/ui";

function fmtSize(b: number) {
  return b > 1024 * 1024 ? `${(b / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(b / 1024))} KB`;
}

export default function Upload() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [driveQuery, setDriveQuery] = useState("");

  const upload = useMutation({
    mutationFn: api.uploadContract,
    onSuccess: (r) => navigate(`/contracts/${r.contract.id}`),
  });
  const integrations = useQuery({ queryKey: ["integrations"], queryFn: api.integrations });
  const driveConnected = integrations.data?.some((i) => i.key === "gdrive" && i.connected);
  const driveFiles = useQuery({
    queryKey: ["drive", driveQuery],
    queryFn: () => api.driveFiles(driveQuery || undefined),
    enabled: !!driveConnected,
  });
  const driveImport = useMutation({
    mutationFn: api.driveImport,
    onSuccess: (r) => navigate(`/contracts/${r.contract.id}`),
  });

  const pick = (f: File | undefined) => {
    if (f) {
      setFile(f);
      upload.reset();
    }
  };

  return (
    <div className="mx-auto max-w-5xl">
      <PageHeader title="Upload & analyze" description="Drop in a contract — the full pipeline runs locally on your machine." />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-2">
          <Card bodyClassName="p-6">
            <div
              role="button"
              tabIndex={0}
              onClick={() => inputRef.current?.click()}
              onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && inputRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                pick(e.dataTransfer.files[0]);
              }}
              className={cx(
                "flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-14 text-center transition",
                dragging ? "scale-[1.01] border-brand bg-brand-soft" : "border-line hover:border-brand/50 hover:bg-surface-2",
              )}
            >
              <input ref={inputRef} type="file" accept=".pdf,.txt" className="hidden" onChange={(e) => pick(e.target.files?.[0])} />
              <span className="mb-4 grid h-16 w-16 place-items-center rounded-2xl bg-gradient-to-br from-grad-a to-grad-b text-white shadow-pop">
                <UploadCloud className="h-8 w-8" />
              </span>
              <p className="text-base font-semibold">Drag &amp; drop your contract here</p>
              <p className="mt-1 text-sm text-ink-2">
                or <span className="font-medium text-brand">browse files</span> · PDF or TXT, up to 50 MB
              </p>
            </div>

            {file && (
              <div className="mt-5 flex animate-fade-in items-center gap-3 rounded-xl border border-line bg-surface-2 p-3">
                <span className="grid h-10 w-10 place-items-center rounded-lg bg-critical/10 text-critical">
                  <FileText className="h-5 w-5" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{file.name}</p>
                  <p className="text-xs text-muted">{fmtSize(file.size)}</p>
                </div>
                <button onClick={() => setFile(null)} className="rounded-md p-1.5 text-muted hover:bg-surface hover:text-ink" aria-label="Remove file">
                  <X className="h-4 w-4" />
                </button>
                <Button icon={ScanText} loading={upload.isPending} onClick={() => upload.mutate(file)}>
                  Analyze
                </Button>
              </div>
            )}
            <div className="mt-3">
              <ErrorBox error={upload.error} />
            </div>
          </Card>

          <Card title="What happens next" subtitle="Document Upload → OCR → NLP → Term extraction → Risk analysis → Report">
            <PipelineStepper />
          </Card>
        </div>

        <div className="space-y-6">
          <Card title="Built for real-world documents">
            <ul className="space-y-4 text-sm">
              {[
                { i: ScanText, t: "Scanned PDFs", d: "Image-only pages are cleaned up and OCR'd with Tesseract." },
                { i: FileText, t: "Handwritten amendments", d: "Detected and transcribed with TrOCR, flagged for review." },
                { i: Languages, t: "Multiple languages", d: "Language is detected; Spanish, French & German supported." },
                { i: Lock, t: "Private by design", d: "Free local models — nothing is sent to the cloud." },
              ].map(({ i: I, t, d }) => (
                <li key={t} className="flex gap-3">
                  <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-brand-soft text-brand">
                    <I className="h-4 w-4" />
                  </span>
                  <span>
                    <span className="block font-medium">{t}</span>
                    <span className="text-ink-2">{d}</span>
                  </span>
                </li>
              ))}
            </ul>
          </Card>

          <Card title="Import from Google Drive" icon={HardDrive} bodyClassName="p-0">
            {driveConnected ? (
              <>
                <div className="p-4 pb-2">
                  <input value={driveQuery} onChange={(e) => setDriveQuery(e.target.value)} placeholder="Search Drive…" className="input" />
                </div>
                <div className="px-4">
                  <ErrorBox error={driveFiles.error ?? driveImport.error} />
                </div>
                <ul className="max-h-72 divide-y divide-line overflow-y-auto">
                  {driveFiles.data?.map((f) => (
                    <li key={f.id} className="flex items-center gap-2 px-4 py-2.5 text-sm">
                      <span className="min-w-0 flex-1">
                        <span className="block truncate">{f.name}</span>
                        <span className="text-xs text-muted">{formatDate(f.modified)}</span>
                      </span>
                      <Button size="sm" variant="secondary" icon={CloudDownload} disabled={driveImport.isPending} onClick={() => driveImport.mutate(f.id)}>
                        Import
                      </Button>
                    </li>
                  ))}
                </ul>
              </>
            ) : (
              <EmptyState icon={HardDrive} title="Not connected" description="Enable Google Drive in Settings to import contracts directly." />
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
