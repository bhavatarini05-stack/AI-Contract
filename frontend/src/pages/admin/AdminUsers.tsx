import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { KeyRound, Search, ShieldCheck, Trash2, UserPlus, UserRound, Users, X } from "lucide-react";
import { api } from "../../api/client";
import type { AdminUser } from "../../api/types";
import { Avatar } from "../../components/Layout";
import { Button, Card, EmptyState, ErrorBox, PageHeader, Select, Skeleton, cx, formatDate } from "../../components/ui";
import { useAuth } from "../../lib/auth";

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center p-4" role="dialog" aria-modal="true" aria-label={title}>
      <div className="absolute inset-0 bg-ink/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-md animate-fade-in rounded-2xl border border-line bg-surface shadow-pop">
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <h2 className="font-semibold">{title}</h2>
          <button onClick={onClose} className="rounded-md p-1 text-muted hover:bg-surface-2 hover:text-ink" aria-label="Close">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

function CreateUserModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [form, setForm] = useState({ name: "", email: "", password: "", role: "user" });
  const create = useMutation({
    mutationFn: () => api.adminCreateUser(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      onClose();
    },
  });
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm({ ...form, [k]: e.target.value });
  return (
    <Modal title="Add user" onClose={onClose}>
      <form
        className="space-y-4"
        onSubmit={(e) => {
          e.preventDefault();
          create.mutate();
        }}
      >
        <div>
          <label className="label">Full name</label>
          <input className="input" value={form.name} onChange={set("name")} autoFocus />
        </div>
        <div>
          <label className="label">Email</label>
          <input className="input" type="email" value={form.email} onChange={set("email")} />
        </div>
        <div>
          <label className="label">Temporary password</label>
          <input className="input" type="text" value={form.password} onChange={set("password")} placeholder="At least 8 characters" />
          <p className="mt-1 text-xs text-muted">Share it securely; the user can change it from their profile.</p>
        </div>
        <div>
          <label className="label">Role</label>
          <Select value={form.role} onChange={set("role")} className="w-full">
            <option value="user">User — own contracts only</option>
            <option value="admin">Admin — full access</option>
          </Select>
        </div>
        <ErrorBox error={create.error} />
        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" icon={UserPlus} loading={create.isPending} disabled={form.name.length < 2 || !form.email || form.password.length < 8}>
            Create user
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ResetPasswordModal({ user, onClose }: { user: AdminUser; onClose: () => void }) {
  const [password, setPassword] = useState("");
  const reset = useMutation({ mutationFn: () => api.adminUpdateUser(user.id, { password }), onSuccess: onClose });
  return (
    <Modal title={`Reset password · ${user.name}`} onClose={onClose}>
      <div className="space-y-4">
        <div>
          <label className="label">New temporary password</label>
          <input className="input" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="At least 8 characters" autoFocus />
        </div>
        <ErrorBox error={reset.error} />
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button icon={KeyRound} loading={reset.isPending} disabled={password.length < 8} onClick={() => reset.mutate()}>
            Reset password
          </Button>
        </div>
      </div>
    </Modal>
  );
}

export default function AdminUsers() {
  const qc = useQueryClient();
  const { user: me } = useAuth();
  const q = useQuery({ queryKey: ["admin-users"], queryFn: api.adminUsers });
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
  const [resetting, setResetting] = useState<AdminUser | null>(null);

  const refresh = () => qc.invalidateQueries({ queryKey: ["admin-users"] });
  const update = useMutation({
    mutationFn: ({ id, patch }: { id: number; patch: { role?: string; is_active?: boolean } }) => api.adminUpdateUser(id, patch),
    onSuccess: refresh,
  });
  const del = useMutation({ mutationFn: api.adminDeleteUser, onSuccess: refresh });

  const rows = useMemo(() => {
    const s = search.trim().toLowerCase();
    return (q.data ?? []).filter((u) => !s || u.name.toLowerCase().includes(s) || u.email.toLowerCase().includes(s));
  }, [q.data, search]);

  return (
    <div>
      <PageHeader
        title="Users"
        description="Create accounts, assign roles and control access."
        actions={
          <Button icon={UserPlus} onClick={() => setCreating(true)}>
            Add user
          </Button>
        }
      />
      <Card bodyClassName="p-0">
        <div className="flex flex-wrap items-center gap-3 border-b border-line p-4">
          <div className="relative min-w-[220px] flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input className="input pl-9" placeholder="Search by name or email…" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <span className="text-xs text-muted">{rows.length} user(s)</span>
        </div>
        <div className="px-4 pt-3">
          <ErrorBox error={q.error ?? update.error ?? del.error} />
        </div>
        {q.isLoading ? (
          <div className="space-y-3 p-5">
            <Skeleton className="h-12" />
            <Skeleton className="h-12" />
          </div>
        ) : !rows.length ? (
          <EmptyState icon={Users} title="No users found" />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-[11px] font-semibold uppercase tracking-wider text-muted">
                  <th className="px-5 py-3">User</th>
                  <th className="px-3 py-3">Role</th>
                  <th className="px-3 py-3">Status</th>
                  <th className="px-3 py-3 text-right">Contracts</th>
                  <th className="px-3 py-3">Last sign-in</th>
                  <th className="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {rows.map((u) => {
                  const self = u.id === me?.id;
                  return (
                    <tr key={u.id} className={cx("transition hover:bg-surface-2", !u.is_active && "opacity-60")}>
                      <td className="px-5 py-3">
                        <div className="flex items-center gap-3">
                          <Avatar name={u.name} size="sm" />
                          <div className="min-w-0">
                            <p className="truncate font-medium">
                              {u.name} {self && <span className="text-xs font-normal text-muted">(you)</span>}
                            </p>
                            <p className="truncate text-xs text-muted">{u.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-3">
                        <Select
                          aria-label={`Role for ${u.name}`}
                          value={u.role}
                          disabled={self}
                          onChange={(e) => update.mutate({ id: u.id, patch: { role: e.target.value } })}
                          className="py-1 text-xs"
                        >
                          <option value="user">User</option>
                          <option value="admin">Admin</option>
                        </Select>
                      </td>
                      <td className="px-3 py-3">
                        <button
                          disabled={self}
                          onClick={() => update.mutate({ id: u.id, patch: { is_active: !u.is_active } })}
                          className={cx(
                            "inline-flex items-center gap-2 rounded-full px-1 py-0.5 text-xs font-medium disabled:cursor-not-allowed",
                          )}
                          aria-label={u.is_active ? "Deactivate user" : "Activate user"}
                          title={self ? "You can't deactivate yourself" : u.is_active ? "Click to deactivate" : "Click to activate"}
                        >
                          <span className={cx("relative h-5 w-9 rounded-full transition", u.is_active ? "bg-good" : "bg-track")}>
                            <span className={cx("absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition-all", u.is_active ? "left-[18px]" : "left-0.5")} />
                          </span>
                          {u.is_active ? "Active" : "Disabled"}
                        </button>
                      </td>
                      <td className="tnum px-3 py-3 text-right font-medium">{u.contracts}</td>
                      <td className="whitespace-nowrap px-3 py-3 text-ink-2">{u.last_login ? formatDate(u.last_login) : "Never"}</td>
                      <td className="px-5 py-3">
                        <div className="flex justify-end gap-1.5">
                          <Button size="sm" variant="secondary" icon={KeyRound} onClick={() => setResetting(u)}>
                            Reset
                          </Button>
                          <Button
                            size="sm"
                            variant="danger"
                            icon={Trash2}
                            disabled={self}
                            onClick={() => confirm(`Delete ${u.name} and all of their ${u.contracts} contract(s)? This cannot be undone.`) && del.mutate(u.id)}
                          >
                            Delete
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        <div className="flex flex-wrap gap-4 border-t border-line px-5 py-3 text-xs text-ink-2">
          <span className="inline-flex items-center gap-1.5">
            <ShieldCheck className="h-3.5 w-3.5 text-brand" /> Admin: all contracts, users, templates, policies, integrations
          </span>
          <span className="inline-flex items-center gap-1.5">
            <UserRound className="h-3.5 w-3.5" /> User: only their own contracts
          </span>
        </div>
      </Card>
      {creating && <CreateUserModal onClose={() => setCreating(false)} />}
      {resetting && <ResetPasswordModal user={resetting} onClose={() => setResetting(null)} />}
    </div>
  );
}
