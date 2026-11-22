import type {
  AdminContract,
  AdminStats,
  AdminUser,
  Alert,
  ComplianceResult,
  CompareResult,
  ContractDetail,
  ContractSummary,
  Health,
  Integration,
  Job,
  Obligation,
  Policy,
  PolicyRule,
  SignatureRequest,
  Template,
  User,
} from "./types";

export const API_BASE = "/api";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (res.status === 401 && !path.startsWith("/auth/")) {
    window.dispatchEvent(new Event("auth:unauthorized"));
  }
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const body = await res.json();
      msg = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail ?? body);
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, msg);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  health: () => request<Health>("/health"),

  // ---- auth ----
  authConfig: () => request<{ allow_registration: boolean; first_run: boolean }>("/auth/config"),
  me: () => request<User>("/auth/me"),
  login: (email: string, password: string) => request<User>("/auth/login", json("POST", { email, password })),
  register: (name: string, email: string, password: string) =>
    request<User>("/auth/register", json("POST", { name, email, password })),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  updateProfile: (name: string) => request<User>("/auth/me", json("PATCH", { name })),
  changePassword: (current_password: string, new_password: string) =>
    request<void>("/auth/password", json("POST", { current_password, new_password })),

  // ---- admin ----
  adminStats: () => request<AdminStats>("/admin/stats"),
  adminUsers: () => request<AdminUser[]>("/admin/users"),
  adminCreateUser: (u: { name: string; email: string; password: string; role: string }) =>
    request<User>("/admin/users", json("POST", u)),
  adminUpdateUser: (id: number, patch: Partial<{ name: string; role: string; is_active: boolean; password: string }>) =>
    request<User>(`/admin/users/${id}`, json("PATCH", patch)),
  adminDeleteUser: (id: number) => request<void>(`/admin/users/${id}`, { method: "DELETE" }),
  adminContracts: () => request<AdminContract[]>("/admin/contracts"),


  listContracts: () => request<ContractSummary[]>("/contracts"),
  getContract: (id: number) => request<ContractDetail>(`/contracts/${id}`),
  uploadContract: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return request<{ contract: ContractSummary; job: Job }>("/contracts", { method: "POST", body: fd });
  },
  reanalyze: (id: number) => request<Job>(`/contracts/${id}/reanalyze`, { method: "POST" }),
  deleteContract: (id: number) => request<void>(`/contracts/${id}`, { method: "DELETE" }),
  fileUrl: (id: number) => `${API_BASE}/contracts/${id}/file`,
  reportUrl: (id: number) => `${API_BASE}/contracts/${id}/report`,

  compare: (id: number, templateId: number) => request<CompareResult>(`/contracts/${id}/compare/${templateId}`),
  compliance: (id: number, policyId: number) =>
    request<ComplianceResult>(`/contracts/${id}/compliance/${policyId}`),

  listTemplates: () => request<Template[]>("/templates"),
  createTemplate: (t: { name: string; contract_type?: string; content: string }) =>
    request<Template>("/templates", json("POST", t)),
  uploadTemplate: (name: string, file: File) => {
    const fd = new FormData();
    fd.append("name", name);
    fd.append("file", file);
    return request<Template>("/templates/upload", { method: "POST", body: fd });
  },
  deleteTemplate: (id: number) => request<void>(`/templates/${id}`, { method: "DELETE" }),

  listPolicies: () => request<Policy[]>("/policies"),
  createPolicy: (p: { name: string; description?: string; rules: PolicyRule[] }) =>
    request<Policy>("/policies", json("POST", p)),
  updatePolicy: (id: number, p: { name: string; description?: string | null; rules: PolicyRule[] }) =>
    request<Policy>(`/policies/${id}`, json("PUT", p)),
  deletePolicy: (id: number) => request<void>(`/policies/${id}`, { method: "DELETE" }),

  listObligations: (days?: number, status = "open") => {
    const q = new URLSearchParams({ status });
    if (days !== undefined) q.set("days", String(days));
    return request<Obligation[]>(`/obligations?${q}`);
  },
  updateObligation: (id: number, status: string) =>
    request<Obligation>(`/obligations/${id}`, json("PATCH", { status })),
  listAlerts: (unreadOnly = true) => request<Alert[]>(`/alerts?unread_only=${unreadOnly}`),
  markAlertRead: (id: number) => request<Alert>(`/alerts/${id}/read`, { method: "POST" }),

  integrations: () => request<Integration[]>("/integrations"),
  connect: (key: string) => request<{ authorize_url: string }>(`/integrations/${key}/connect`),
  disconnect: (key: string) => request<void>(`/integrations/${key}/connection`, { method: "DELETE" }),
  driveFiles: (q?: string) =>
    request<{ id: string; name: string; mime_type: string; modified: string | null }[]>(
      `/integrations/gdrive/files${q ? `?q=${encodeURIComponent(q)}` : ""}`,
    ),
  driveImport: (fileId: string) =>
    request<{ contract: ContractSummary; job: Job }>(`/integrations/gdrive/import/${fileId}`, { method: "POST" }),
  driveExport: (contractId: number) =>
    request<{ file_id: string; name: string }>(`/integrations/gdrive/export/${contractId}`, { method: "POST" }),
  sendForSignature: (provider: string, contractId: number, signers: { name: string; email: string }[]) =>
    request<SignatureRequest>(`/integrations/${provider}/send/${contractId}`, json("POST", { signers })),
  signatureRequests: (contractId: number) =>
    request<SignatureRequest[]>(`/integrations/signature-requests?contract_id=${contractId}`),
  refreshSignature: (id: number) =>
    request<SignatureRequest>(`/integrations/signature-requests/${id}/refresh`, { method: "POST" }),
};
