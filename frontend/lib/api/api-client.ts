import type { ContractStatus } from "@/components/ui/status-badge";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type RiskLevel = "low" | "medium" | "high";

export interface ContractSummary {
  id: string;
  file_name: string;
  contract_type: string | null;
  status: ContractStatus;
  overall_risk: RiskLevel | null;
  clause_count: number;
  created_at: string;
  analyzed_at: string | null;
}

export interface ContractListResponse {
  items: ContractSummary[];
  total: number;
  page: number;
  size: number;
}

export interface ContractUploadResponse {
  id: string;
  file_name: string;
  status: ContractStatus;
  message: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number
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
 * When called from a Server Component, forward the incoming request's
 * cookies to the backend. Node's fetch has no cookie jar, so we do it
 * manually. On the client, the browser handles cookies on same-site
 * requests automatically (and for cross-origin we'd need CORS + credentials,
 * but API calls from the browser today go through the Next server).
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
    throw new ApiError(`API request failed: ${res.statusText}`, res.status);
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
