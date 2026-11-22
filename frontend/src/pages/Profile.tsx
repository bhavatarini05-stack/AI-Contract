import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { KeyRound, Save, ShieldCheck, UserRound } from "lucide-react";
import { api } from "../api/client";
import { Avatar } from "../components/Layout";
import { Button, Card, ErrorBox, Notice, PageHeader, formatDate } from "../components/ui";
import { useAuth } from "../lib/auth";
import { StrengthMeter } from "./auth/Register";

export default function Profile() {
  const { user, isAdmin } = useAuth();
  const qc = useQueryClient();
  const [name, setName] = useState(user?.name ?? "");
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");

  const saveName = useMutation({
    mutationFn: () => api.updateProfile(name.trim()),
    onSuccess: (u) => qc.setQueryData(["me"], u),
  });
  const changePw = useMutation({
    mutationFn: () => api.changePassword(current, next),
    onSuccess: () => {
      setCurrent("");
      setNext("");
      setConfirm("");
    },
  });

  if (!user) return null;
  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader title="Profile" description="Your account details and password." />
      <div className="grid gap-6 md:grid-cols-5">
        <Card className="md:col-span-2" bodyClassName="p-6">
          <div className="flex flex-col items-center text-center">
            <Avatar name={user.name} size="lg" />
            <p className="mt-3 text-lg font-semibold">{user.name}</p>
            <p className="text-sm text-ink-2">{user.email}</p>
            <span className="mt-2 inline-flex items-center gap-1 rounded-full bg-brand-soft px-2.5 py-1 text-xs font-semibold uppercase tracking-wide text-brand">
              {isAdmin ? <ShieldCheck className="h-3.5 w-3.5" /> : <UserRound className="h-3.5 w-3.5" />}
              {user.role}
            </span>
          </div>
          <dl className="mt-6 space-y-2 border-t border-line pt-4 text-sm">
            <div className="flex justify-between">
              <dt className="text-ink-2">Member since</dt>
              <dd>{formatDate(user.created_at)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-ink-2">Last sign-in</dt>
              <dd>{formatDate(user.last_login)}</dd>
            </div>
          </dl>
        </Card>

        <div className="space-y-6 md:col-span-3">
          <Card title="Personal details" icon={UserRound}>
            <label className="label" htmlFor="name">
              Full name
            </label>
            <div className="flex gap-2">
              <input id="name" className="input" value={name} onChange={(e) => setName(e.target.value)} />
              <Button icon={Save} loading={saveName.isPending} disabled={name.trim().length < 2 || name.trim() === user.name} onClick={() => saveName.mutate()}>
                Save
              </Button>
            </div>
            <div className="mt-3 space-y-2">
              {saveName.isSuccess && <Notice tone="good">Name updated.</Notice>}
              <ErrorBox error={saveName.error} />
            </div>
          </Card>

          <Card title="Change password" icon={KeyRound}>
            <form
              className="space-y-4"
              onSubmit={(e) => {
                e.preventDefault();
                changePw.mutate();
              }}
            >
              <div>
                <label className="label" htmlFor="cur">
                  Current password
                </label>
                <input id="cur" type="password" autoComplete="current-password" className="input" value={current} onChange={(e) => setCurrent(e.target.value)} />
              </div>
              <div>
                <label className="label" htmlFor="new">
                  New password
                </label>
                <input id="new" type="password" autoComplete="new-password" className="input" value={next} onChange={(e) => setNext(e.target.value)} />
                <StrengthMeter password={next} />
              </div>
              <div>
                <label className="label" htmlFor="conf">
                  Confirm new password
                </label>
                <input id="conf" type="password" autoComplete="new-password" className="input" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
                {confirm && confirm !== next && <p className="mt-1 text-xs text-critical">Passwords don't match</p>}
              </div>
              <Button type="submit" icon={KeyRound} loading={changePw.isPending} disabled={!current || next.length < 8 || next !== confirm}>
                Update password
              </Button>
              {changePw.isSuccess && <Notice tone="good">Password changed.</Notice>}
              <ErrorBox error={changePw.error} />
            </form>
          </Card>
        </div>
      </div>
    </div>
  );
}
