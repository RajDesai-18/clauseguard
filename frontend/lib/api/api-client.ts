import type { ContractStatus } from "@/components/ui/status-badge";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type RiskLevel = "low" | "medium" | "high";
export type ClauseRiskLevel = "green" | "yellow" | "red";

export interface ContractSummary {
  id: string;
  file_name: string;
  contract_type: string | null;
  status: ContractStatus;
  overall_risk: RiskLevel | null;
  clause_count: number;
  degraded_reason: string | null;
  created_at: string;
  analyzed_at: string | null;
}

export interface ContractListResponse {
  items: ContractSummary[];
  total: number;
  page: number;
  size: number;
}

export interface ContractDetail extends ContractSummary {
  summary: string | null;
  file_url: string;
}

export interface ContractUploadResponse {
  id: string;
  file_name: string;
  status: ContractStatus;
  message: string;
}

/**
 * A single clause as returned by GET /contracts/{id}/clauses.
 *
 * Note: risk_level, explanation, and confidence are typed as nullable
 * defensively. The backend Pydantic schema currently marks them as
 * required, but the underlying DB model allows nulls (clauses can be
 * persisted with clause_type set before analysis assigns risk_level).
 * If a mid-pipeline clause ever slips through, the frontend won't
 * crash on it.
 */
export interface ClauseDetail {
  id: string;
  clause_type: string;
  original_text: string;
  position: number;
  risk_level: ClauseRiskLevel | null;
  confidence: number | null;
  explanation: string | null;
  market_comparison: string | null;
  suggested_redline: string | null;
}

export interface ClauseListResponse {
  contract_id: string;
  contract_type: string | null;
  overall_risk: RiskLevel | null;
  clause_count: number;
  clauses: ClauseDetail[];
}

export interface SearchHit {
  clause_id: string;
  clause_type: string;
  risk_level: ClauseRiskLevel;
  original_text: string;
  explanation: string;
  position: number;
  similarity: number;
}

export interface SearchContractGroup {
  contract_id: string;
  file_name: string;
  contract_type: string | null;
  overall_risk: RiskLevel | null;
  top_similarity: number;
  hits: SearchHit[];
}

export interface SearchResponse {
  query: string;
  total_hits: number;
  groups: SearchContractGroup[];
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
    public requestId?: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Raised specifically for 401 responses. Lets Server Components
 * distinguish "user is not authenticated" from "backend is down".
 */
export class UnauthorizedError extends ApiError {
  constructor(message = "Authentication required.") {
    super(message, 401);
    this.name = "UnauthorizedError";
  }
}

/**
 * Parse the backend's structured error envelope from a failed response.
 *
 * The API returns { error: { code, message, request_id, details } } on
 * every error (see backend app/core/errors.py). We pull the human
 * message, the stable code, and the request_id so the UI can show a
 * useful message and a support reference instead of a bare status.
 * Falls back gracefully if the body isn't our envelope shape.
 */
async function parseApiError(res: Response): Promise<ApiError> {
  let message = `API request failed: ${res.statusText}`;
  let code: string | undefined;
  let requestId: string | undefined;

  try {
    const body = await res.json();
    if (body?.error && typeof body.error === "object") {
      if (typeof body.error.message === "string") message = body.error.message;
      if (typeof body.error.code === "string") code = body.error.code;
      if (typeof body.error.request_id === "string") requestId = body.error.request_id;
    } else if (typeof body?.detail === "string") {
      // Fallback for any endpoint still emitting FastAPI's default shape.
      message = body.detail;
    }
  } catch {
    // Non-JSON body; keep the statusText-based default message.
  }

  return new ApiError(message, res.status, code, requestId);
}

/**
 * When called from a Server Component or route handler, forward the
 * incoming request's cookies to the backend. Node's fetch has no
 * cookie jar, so we do it manually.
 */
async function buildServerCookieHeader(): Promise<string | null> {
  if (typeof window !== "undefined") return null;
  // Dynamic import so this file remains usable in Client Components too.
  // next/headers is only callable on the server side of the request boundary.
  const { cookies } = await import("next/headers");
  const jar = await cookies();
  const all = jar.getAll();
  if (all.length === 0) return null;
  return all.map((c) => `${c.name}=${c.value}`).join("; ");
}

/**
 * Server-side request helper. Forwards cookies via next/headers.
 * Use the *Client variants below from Client Components.
 */
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const serverCookieHeader = await buildServerCookieHeader();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init?.headers as Record<string, string>) ?? {}),
  };
  if (serverCookieHeader) {
    headers["Cookie"] = serverCookieHeader;
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
    credentials: "include",
  });

  if (res.status === 401) {
    throw new UnauthorizedError();
  }
  if (!res.ok) {
    throw await parseApiError(res);
  }

  return res.json() as Promise<T>;
}

/**
 * Client-side request helper. Relies on the browser's cookie jar plus
 * `credentials: "include"`. Does NOT touch next/headers, so it's safe
 * to call from Client Components without bundler ambiguity.
 */
async function requestClient<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init?.headers as Record<string, string>) ?? {}),
  };

  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
    credentials: "include",
  });

  if (res.status === 401) {
    throw new UnauthorizedError();
  }
  if (!res.ok) {
    throw await parseApiError(res);
  }

  return res.json() as Promise<T>;
}

export async function listContracts(params?: {
  page?: number;
  size?: number;
}): Promise<ContractListResponse> {
  const query = new URLSearchParams();
  if (params?.page) query.set("page", String(params.page));
  if (params?.size) query.set("size", String(params.size));
  const qs = query.toString();
  return request<ContractListResponse>(`/api/v1/contracts${qs ? `?${qs}` : ""}`);
}

export async function getContract(id: string): Promise<ContractDetail> {
  return request<ContractDetail>(`/api/v1/contracts/${id}`);
}

/**
 * Client-side equivalent of getContract(). Use this from "use client"
 * components where next/headers isn't available.
 */
export async function getContractClient(id: string): Promise<ContractDetail> {
  return requestClient<ContractDetail>(`/api/v1/contracts/${id}`);
}

/**
 * List all clauses for a contract. Server-side only; the analysis
 * page is a Server Component so this is fetched once at request time.
 */
export async function listClauses(id: string): Promise<ClauseListResponse> {
  return request<ClauseListResponse>(`/api/v1/contracts/${id}/clauses`);
}

/**
 * Client-side equivalent of listClauses(). Use this from "use client"
 * components where next/headers isn't available, e.g. to refetch clauses
 * after an SSE "complete" event without a full page reload.
 */
export async function listClausesClient(id: string): Promise<ClauseListResponse> {
  return requestClient<ClauseListResponse>(`/api/v1/contracts/${id}/clauses`);
}

export async function uploadContract(file: File): Promise<ContractUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const serverCookieHeader = await buildServerCookieHeader();
  const headers: Record<string, string> = {};
  if (serverCookieHeader) {
    headers["Cookie"] = serverCookieHeader;
  }

  const res = await fetch(`${API_URL}/api/v1/contracts/upload`, {
    method: "POST",
    body: formData,
    headers,
    cache: "no-store",
    credentials: "include",
  });

  if (res.status === 401) {
    throw new UnauthorizedError();
  }
  if (!res.ok) {
    let detail = `Upload failed: ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // ignore parse error, use default message
    }
    throw new ApiError(detail, res.status);
  }

  return res.json() as Promise<ContractUploadResponse>;
}

export async function deleteContract(id: string): Promise<void> {
  const url = `${API_URL}/api/v1/contracts/${id}`;
  const response = await fetch(url, {
    method: "DELETE",
    credentials: "include",
  });

  if (!response.ok) {
    // Try to surface a useful detail from the backend.
    let detail: string | undefined;
    try {
      const body = await response.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // Non-JSON response; fall back to status text.
    }
    throw new ApiError(detail ?? response.statusText, response.status);
  }
  // 204 No Content — no body to parse.
}

/**
 * Cross-contract semantic clause search. Client-side: the search page is
 * interactive (query box, live results), so it uses the browser cookie jar
 * via requestClient rather than next/headers.
 */
export async function searchClausesClient(query: string, limit?: number): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query });
  if (limit) params.set("limit", String(limit));
  return requestClient<SearchResponse>(`/api/v1/search?${params.toString()}`);
}
