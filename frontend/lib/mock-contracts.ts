import type { ContractStatus } from "@/components/ui/status-badge";

export interface MockContract {
  id: string;
  fileName: string;
  contractType: string;
  status: ContractStatus;
  overallRisk: "low" | "medium" | "high" | null;
  clauseCount: number;
  createdAt: string;
  analyzedAt: string | null;
}

export const MOCK_CONTRACTS: MockContract[] = [
  {
    id: "c-01",
    fileName: "Acme_MSA_2026_v3.pdf",
    contractType: "MSA",
    status: "complete",
    overallRisk: "high",
    clauseCount: 47,
    createdAt: "2026-04-18T10:22:00Z",
    analyzedAt: "2026-04-18T10:24:12Z",
  },
  {
    id: "c-02",
    fileName: "Northwind_NDA_mutual.docx",
    contractType: "NDA",
    status: "complete",
    overallRisk: "low",
    clauseCount: 12,
    createdAt: "2026-04-17T15:40:00Z",
    analyzedAt: "2026-04-17T15:41:05Z",
  },
  {
    id: "c-03",
    fileName: "Freelance_SOW_Q2.pdf",
    contractType: "SOW",
    status: "analyzing",
    overallRisk: null,
    clauseCount: 0,
    createdAt: "2026-04-21T09:15:00Z",
    analyzedAt: null,
  },
  {
    id: "c-04",
    fileName: "Vendor_Services_Agreement.pdf",
    contractType: "MSA",
    status: "complete",
    overallRisk: "medium",
    clauseCount: 28,
    createdAt: "2026-04-16T11:08:00Z",
    analyzedAt: "2026-04-16T11:10:44Z",
  },
  {
    id: "c-05",
    fileName: "Employment_Contract_draft.docx",
    contractType: "Other",
    status: "failed",
    overallRisk: null,
    clauseCount: 0,
    createdAt: "2026-04-20T14:30:00Z",
    analyzedAt: null,
  },
  {
    id: "c-06",
    fileName: "Advisor_Agreement_2026.pdf",
    contractType: "Other",
    status: "complete",
    overallRisk: "low",
    clauseCount: 18,
    createdAt: "2026-04-15T08:22:00Z",
    analyzedAt: "2026-04-15T08:23:18Z",
  },
];

export function formatRelativeDate(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
