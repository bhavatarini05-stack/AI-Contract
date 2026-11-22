export type Severity = "low" | "medium" | "high" | "critical";

export interface Job {
  id: number;
  contract_id: number;
  stage: string;
  progress: number;
  status: "queued" | "running" | "done" | "failed";
  error: string | null;
}

export interface ContractSummary {
  id: number;
  filename: string;
  status: "uploaded" | "processing" | "done" | "failed";
  page_count: number | null;
  language: string | null;
  contract_type: string | null;
  governing_law: string | null;
  effective_date: string | null;
  expiry_date: string | null;
  uploaded_at: string;
  risk_score: number | null;
  risk_level: Severity | null;
}

export interface Clause {
  id: number;
  type: string;
  heading: string | null;
  text: string;
  page: number | null;
  confidence: number;
  source: string;
  needs_review: boolean;
}

export interface Term {
  id: number;
  key: string;
  label: string;
  display: string;
  raw_text: string | null;
  page: number | null;
}

export interface RiskFlag {
  id: number;
  rule_id: string;
  category: string;
  severity: Severity;
  message: string;
  suggestion: string | null;
  evidence: string | null;
  page: number | null;
  source: string;
}

export interface Obligation {
  id: number;
  contract_id: number;
  kind: string;
  description: string;
  due_date: string | null;
  status: string;
  page: number | null;
  contract_filename?: string;
  days_left?: number | null;
}

export interface Negotiation {
  priority: Severity;
  category: string;
  suggestion: string;
  standard_position: string | null;
  source: string;
}

export interface Report {
  summary: string;
  key_points: string[] | null;
  risk_score: number;
  risk_level: Severity;
  negotiation: Negotiation[] | null;
  llm_model: string | null;
  generated_at: string;
}

export interface ContractDetail extends ContractSummary {
  type_confidence: number | null;
  parties: { name: string; role: string }[] | null;
  page_info: { page: number; ocr: boolean; ocr_confidence: number | null; handwriting: string[] }[] | null;
  warnings: string[] | null;
  clauses: Clause[];
  terms: Term[];
  risk_flags: RiskFlag[];
  obligations: Obligation[];
  report: Report | null;
  latest_job: Job | null;
  owner: { id: number; name: string; email: string } | null;
  is_mine: boolean;
}

export interface Template {
  id: number;
  name: string;
  contract_type: string | null;
  content: string;
}

export interface PolicyRule {
  id: string;
  requirement: string;
  clause_types?: string[];
  must_include?: string[];
  must_not_include?: string[];
  severity?: Severity;
}

export interface Policy {
  id: number;
  name: string;
  description: string | null;
  rules: PolicyRule[];
}

export interface CompareResult {
  template: { id: number; name: string };
  counts: Record<"same" | "changed" | "missing" | "added", number>;
  terms: { key: string; label: string; contract: string; template: string; differs: boolean }[];
  clauses: {
    clause_type: string;
    label: string;
    status: "same" | "changed" | "missing" | "added";
    similarity: number;
    diff: { op: "equal" | "insert" | "delete"; text: string }[];
    page: number | null;
    explanation: string | null;
    less_favourable?: boolean | null;
  }[];
}

export interface ComplianceResult {
  policy: { id: number; name: string };
  overall: "compliant" | "non_compliant" | "needs_review";
  passed: number;
  failed: number;
  unclear: number;
  results: {
    id: string;
    requirement: string;
    severity: Severity;
    verdict: "pass" | "fail" | "unclear";
    explanation: string;
    evidence: string;
    page: number | null;
    source: string;
  }[];
}

export interface Alert {
  id: number;
  contract_id: number;
  message: string;
  threshold_days: number;
  read: boolean;
  created_at: string;
}

export interface Integration {
  key: string;
  label: string;
  kind: "signature" | "storage";
  configured: boolean;
  connected: boolean;
  oauth: boolean;
}

export interface SignatureRequest {
  id: number;
  contract_id: number;
  provider: string;
  external_id: string;
  status: string;
  signers: { name: string; email: string }[];
  created_at: string;
  imported_contract_id?: number | null;
}

export interface Health {
  status: string;
  llm: { ok: boolean; provider: string; model: string; hint?: string | null; error?: string };
  ocr: { tesseract: boolean; languages: string };
  handwriting: { trocr: boolean };
}

export type Role = "user" | "admin";

export interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

export interface AdminUser extends User {
  contracts: number;
}

export interface AdminContract extends ContractSummary {
  owner_name: string | null;
  owner_email: string | null;
}

export interface AdminStats {
  users: number;
  active_users: number;
  admins: number;
  contracts: number;
  by_status: Record<string, number>;
  by_risk_level: Partial<Record<Severity, number>>;
  avg_risk_score: number | null;
  deadlines_30d: number;
  contracts_per_user: { user_id: number; name: string; contracts: number }[];
  recent_activity: {
    job_id: number;
    contract_id: number;
    filename: string;
    owner: string | null;
    status: string;
    stage: string;
    created_at: string;
  }[];
}
