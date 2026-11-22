import type { ReactNode } from "react";
import { BookOpenCheck, CalendarClock, FileSearch, Lock, Moon, ShieldAlert, Sparkles, Sun } from "lucide-react";
import { useTheme } from "../../lib/theme";

const FEATURES = [
  { icon: FileSearch, title: "Clause & term extraction", text: "Termination, liability, renewal, payment — normalized automatically." },
  { icon: ShieldAlert, title: "Risk flagging & scoring", text: "“Liability cap is missing — standard is 1x fees.”" },
  { icon: CalendarClock, title: "Deadlines & alerts", text: "Never miss a renewal notice or an expiry again." },
  { icon: Lock, title: "Private by design", text: "Free open-source AI that runs entirely on your machine." },
];

export default function AuthLayout({ children }: { children: ReactNode }) {
  const { theme, toggle } = useTheme();
  return (
    <div className="grid min-h-screen lg:grid-cols-[1.05fr_1fr]">
      {/* brand panel */}
      <aside className="relative hidden overflow-hidden bg-gradient-to-br from-grad-a via-[#5b3fe0] to-grad-b p-12 text-white lg:flex lg:flex-col">
        <div className="absolute -left-24 top-1/3 h-96 w-96 rounded-full bg-white/10 blur-3xl" aria-hidden />
        <div className="absolute -right-20 -top-20 h-80 w-80 rounded-full bg-fuchsia-300/20 blur-3xl" aria-hidden />
        <div
          className="absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage: "linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)",
            backgroundSize: "36px 36px",
          }}
          aria-hidden
        />

        <div className="relative flex items-center gap-3">
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-white/15 ring-1 ring-white/25 backdrop-blur">
            <BookOpenCheck className="h-6 w-6" />
          </span>
          <span>
            <span className="block text-lg font-semibold tracking-tight">ClauseLens</span>
            <span className="block text-xs text-white/70">AI contract analyzer</span>
          </span>
        </div>

        <div className="relative my-auto max-w-lg py-12">
          <p className="inline-flex items-center gap-1.5 rounded-full bg-white/15 px-3 py-1 text-xs font-medium ring-1 ring-white/20">
            <Sparkles className="h-3.5 w-3.5" /> Local AI · OCR · NLP · Risk engine
          </p>
          <h1 className="mt-5 text-4xl font-semibold leading-tight tracking-tight">
            Understand every contract <span className="text-white/70">before you sign it.</span>
          </h1>
          <p className="mt-4 text-white/80">
            Upload a PDF and get key terms, risk flags, deadlines and a plain-language summary in minutes.
          </p>

          <ul className="mt-10 grid gap-4 sm:grid-cols-2">
            {FEATURES.map(({ icon: I, title, text }) => (
              <li key={title} className="rounded-2xl bg-white/10 p-4 ring-1 ring-white/15 backdrop-blur-sm">
                <I className="h-5 w-5" />
                <p className="mt-2 text-sm font-semibold">{title}</p>
                <p className="mt-1 text-xs leading-relaxed text-white/75">{text}</p>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs text-white/60">© {new Date().getFullYear()} ClauseLens · AI-generated analysis is not legal advice.</p>
      </aside>

      {/* form panel */}
      <main className="relative flex flex-col bg-page">
        <div className="flex items-center justify-between p-6">
          <span className="flex items-center gap-2 lg:invisible">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-grad-a to-grad-b text-white">
              <BookOpenCheck className="h-5 w-5" />
            </span>
            <span className="font-semibold">ClauseLens</span>
          </span>
          <button
            onClick={toggle}
            className="grid h-9 w-9 place-items-center rounded-lg border border-line bg-surface text-ink-2 hover:text-ink"
            aria-label="Toggle theme"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
        </div>
        <div className="flex flex-1 items-center justify-center px-6 pb-16">
          <div className="w-full max-w-[400px] animate-fade-in">{children}</div>
        </div>
      </main>
    </div>
  );
}
