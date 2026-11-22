import { Brain, Check, FileSearch, FileText, ListChecks, Loader2, ScanText, ShieldAlert } from "lucide-react";
import { cx, type Icon } from "./ui";

/** User-facing pipeline steps, mapped from backend job stages. */
export const STEPS: { id: string; label: string; detail: string; icon: Icon; stages: string[] }[] = [
  { id: "upload", label: "Upload", detail: "PDF received", icon: FileText, stages: ["queued"] },
  { id: "ocr", label: "Text & OCR", detail: "Extract text, OCR scans, detect language", icon: ScanText, stages: ["ingest", "language"] },
  { id: "nlp", label: "Classify & NER", detail: "Contract type, parties, law, dates", icon: Brain, stages: ["classify", "entities"] },
  { id: "terms", label: "Clauses & terms", detail: "Find clauses, normalize terms", icon: FileSearch, stages: ["clauses", "terms"] },
  { id: "risk", label: "Risk analysis", detail: "Rules + local LLM review, deadlines", icon: ShieldAlert, stages: ["risk", "obligations"] },
  { id: "report", label: "Summary & report", detail: "Plain-language summary, suggestions", icon: ListChecks, stages: ["summary", "done"] },
];

export function stepIndex(stage: string | undefined, status?: string) {
  if (status === "done") return STEPS.length;
  const i = STEPS.findIndex((s) => s.stages.includes(stage ?? "queued"));
  return i < 0 ? 0 : i;
}

export default function PipelineStepper({
  stage,
  status,
  progress,
  compact = false,
}: {
  stage?: string;
  status?: string;
  progress?: number;
  compact?: boolean;
}) {
  const current = stepIndex(stage, status);
  const failed = status === "failed";
  return (
    <div>
      <ol className={cx("grid gap-2", compact ? "grid-cols-6" : "grid-cols-2 sm:grid-cols-3")}>
        {STEPS.map((s, i) => {
          const done = i < current;
          const active = i === current && !failed && status !== undefined;
          const I = s.icon;
          return (
            <li
              key={s.id}
              className={cx(
                "relative rounded-xl border p-3 transition",
                done ? "border-good/30 bg-good/5" : active ? "border-brand/40 bg-brand-soft" : "border-line bg-surface",
                compact && "p-2",
              )}
            >
              <div className="flex items-center gap-2">
                <span
                  className={cx(
                    "grid h-7 w-7 shrink-0 place-items-center rounded-lg",
                    done ? "bg-good text-white" : active ? "bg-brand text-white" : "bg-surface-2 text-muted",
                  )}
                >
                  {done ? <Check className="h-4 w-4" /> : active ? <Loader2 className="h-4 w-4 animate-spin" /> : <I className="h-4 w-4" />}
                </span>
                {!compact && <span className={cx("text-sm font-medium", !done && !active && "text-ink-2")}>{s.label}</span>}
              </div>
              {!compact && <p className="mt-1.5 text-xs text-muted">{s.detail}</p>}
              {compact && <p className="mt-1 truncate text-[11px] text-ink-2">{s.label}</p>}
            </li>
          );
        })}
      </ol>
      {progress !== undefined && status !== "done" && (
        <div className="mt-3 flex items-center gap-3">
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-track">
            <div className={cx("h-full rounded-full transition-[width] duration-500", failed ? "bg-critical" : "bg-brand")} style={{ width: `${progress}%` }} />
          </div>
          <span className="tnum w-10 text-right text-xs font-medium text-ink-2">{progress}%</span>
        </div>
      )}
    </div>
  );
}
