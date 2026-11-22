import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRight, Check, Eye, EyeOff, Lock, Mail, User as UserIcon } from "lucide-react";
import { api } from "../../api/client";
import { Button, ErrorBox, Notice, cx } from "../../components/ui";
import { useAuth } from "../../lib/auth";
import AuthLayout from "./AuthLayout";
import { Field } from "./Login";

export function passwordChecks(pw: string) {
  return [
    { ok: pw.length >= 8, label: "At least 8 characters" },
    { ok: /[A-Za-z]/.test(pw) && /\d/.test(pw), label: "Letters and numbers" },
    { ok: pw.length >= 12 || /[^A-Za-z0-9]/.test(pw), label: "12+ characters or a symbol" },
  ];
}

export function StrengthMeter({ password }: { password: string }) {
  const checks = passwordChecks(password);
  const score = checks.filter((c) => c.ok).length;
  const label = ["Too weak", "Weak", "Good", "Strong"][score];
  const color = ["bg-critical", "bg-serious", "bg-warning", "bg-good"][score];
  if (!password) return null;
  return (
    <div className="mt-2">
      <div className="flex gap-1">
        {[0, 1, 2].map((i) => (
          <span key={i} className={cx("h-1 flex-1 rounded-full", i < score ? color : "bg-track")} />
        ))}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-2">
        <span className="font-medium text-ink">{label}</span>
        {checks.map((c) => (
          <span key={c.label} className="inline-flex items-center gap-1">
            <Check className={cx("h-3 w-3", c.ok ? "text-good" : "text-muted")} />
            {c.label}
          </span>
        ))}
      </div>
    </div>
  );
}

export default function Register() {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const config = useQuery({ queryKey: ["auth-config"], queryFn: api.authConfig });
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [show, setShow] = useState(false);
  const [touched, setTouched] = useState(false);

  const mismatch = confirm.length > 0 && confirm !== password;
  const valid = name.trim().length >= 2 && /\S+@\S+\.\S+/.test(email) && password.length >= 8 && password === confirm;

  const register = useMutation({
    mutationFn: () => api.register(name.trim(), email.trim(), password),
    onSuccess: (u) => {
      setUser(u);
      navigate(u.role === "admin" ? "/admin" : "/", { replace: true });
    },
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setTouched(true);
    if (valid) register.mutate();
  };

  const firstRun = config.data?.first_run;

  return (
    <AuthLayout>
      <h2 className="text-2xl font-semibold tracking-tight">{firstRun ? "Set up ClauseLens" : "Create your account"}</h2>
      <p className="mt-1.5 text-sm text-ink-2">
        {firstRun ? "This first account will be the administrator." : "Start analyzing contracts in minutes."}
      </p>

      {firstRun && (
        <div className="mt-6">
          <Notice tone="info">
            <span className="block font-medium">Admin account</span>
            Admins can manage users, templates, policies and integrations.
          </Notice>
        </div>
      )}

      {config.data && !config.data.allow_registration ? (
        <div className="mt-8">
          <Notice>Self-registration is disabled. Ask your administrator to create an account for you.</Notice>
        </div>
      ) : (
        <form onSubmit={submit} className="mt-8 space-y-5" noValidate>
          <Field
            id="name"
            label="Full name"
            icon={UserIcon}
            autoComplete="name"
            placeholder="Jane Doe"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
          />
          <Field
            id="email"
            label="Work email"
            icon={Mail}
            type="email"
            autoComplete="email"
            placeholder="you@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <div>
            <div className="relative">
              <Field
                id="password"
                label="Password"
                icon={Lock}
                type={show ? "text" : "password"}
                autoComplete="new-password"
                placeholder="At least 8 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShow((s) => !s)}
                className="absolute bottom-0 right-0 grid h-11 w-10 place-items-center text-muted hover:text-ink"
                aria-label={show ? "Hide password" : "Show password"}
              >
                {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            <StrengthMeter password={password} />
          </div>
          <div>
            <Field
              id="confirm"
              label="Confirm password"
              icon={Lock}
              type={show ? "text" : "password"}
              autoComplete="new-password"
              placeholder="Repeat password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
            {mismatch && <p className="mt-1.5 text-xs text-critical">Passwords don't match</p>}
          </div>

          {touched && !valid && !mismatch && (
            <p className="text-xs text-critical">Please fill in every field (password at least 8 characters).</p>
          )}
          <ErrorBox error={register.error} />

          <Button type="submit" className="h-11 w-full" loading={register.isPending}>
            {firstRun ? "Create admin account" : "Create account"} <ArrowRight className="h-4 w-4" />
          </Button>
        </form>
      )}

      <p className="mt-8 text-center text-sm text-ink-2">
        Already have an account?{" "}
        <Link to="/login" className="font-medium text-brand hover:underline">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  );
}
