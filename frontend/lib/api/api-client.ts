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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

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

  const res = await fetch(`${API_URL}/api/v1/contracts/upload`, {
    method: "POST",
    body: formData,
    cache: "no-store",
  });

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
