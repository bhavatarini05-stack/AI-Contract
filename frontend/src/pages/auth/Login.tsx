import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ArrowRight, Eye, EyeOff, Lock, Mail } from "lucide-react";
import { api } from "../../api/client";
import { Button, ErrorBox, Notice } from "../../components/ui";
import { useAuth } from "../../lib/auth";
import AuthLayout from "./AuthLayout";

export function Field({
  label,
  icon: I,
  right,
  ...props
}: React.InputHTMLAttributes<HTMLInputElement> & { label: string; icon: typeof Mail; right?: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between">
        <label htmlFor={props.id} className="text-sm font-medium">
          {label}
        </label>
        {right}
      </div>
      <div className="relative">
        <I className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        <input {...props} className="input h-11 pl-10 pr-10" />
      </div>
    </div>
  );
}

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { setUser } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const config = useQuery({ queryKey: ["auth-config"], queryFn: api.authConfig });

  const login = useMutation({
    mutationFn: () => api.login(email.trim(), password),
    onSuccess: (u) => {
      setUser(u);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from && from !== "/login" ? from : u.role === "admin" ? "/admin" : "/", { replace: true });
    },
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    login.mutate();
  };

  return (
    <AuthLayout>
      <h2 className="text-2xl font-semibold tracking-tight">Welcome back</h2>
      <p className="mt-1.5 text-sm text-ink-2">Sign in to review and track your contracts.</p>

      {config.data?.first_run && (
        <div className="mt-6">
          <Notice tone="info">
            First time here? <Link to="/register" className="font-medium text-brand underline">Create the admin account</Link> to set up
            ClauseLens.
          </Notice>
        </div>
      )}

      <form onSubmit={submit} className="mt-8 space-y-5" noValidate>
        <Field
          id="email"
          label="Email"
          icon={Mail}
          type="email"
          autoComplete="email"
          placeholder="you@company.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          autoFocus
        />
        <div className="relative">
          <Field
            id="password"
            label="Password"
            icon={Lock}
            type={show ? "text" : "password"}
            autoComplete="current-password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
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

        <ErrorBox error={login.error} />

        <Button type="submit" className="h-11 w-full" loading={login.isPending} disabled={!email || !password}>
          Sign in <ArrowRight className="h-4 w-4" />
        </Button>
      </form>

      {config.data?.allow_registration && (
        <p className="mt-8 text-center text-sm text-ink-2">
          Don't have an account?{" "}
          <Link to="/register" className="font-medium text-brand hover:underline">
            Create one
          </Link>
        </p>
      )}
      {config.data && !config.data.allow_registration && (
        <p className="mt-8 text-center text-xs text-muted">Accounts are created by your administrator.</p>
      )}
    </AuthLayout>
  );
}
