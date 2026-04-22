import { notFound } from "next/navigation";
import Link from "next/link";
import { ContractDetailView } from "@/components/features/contract-detail-view";
import { ApiError } from "@/lib/api/api-client";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface PageProps {
  params: Promise<{ id: string }>;
}

interface ContractDetail {
  id: string;
  file_name: string;
  contract_type: string | null;
  status: string;
  overall_risk: "low" | "medium" | "high" | null;
  clause_count: number;
  created_at: string;
  analyzed_at: string | null;
  summary: string | null;
  file_url: string;
}

async function fetchContract(id: string): Promise<ContractDetail> {
  const res = await fetch(`${API_URL}/api/v1/contracts/${id}`, {
    cache: "no-store",
  });
  if (res.status === 404) {
    notFound();
  }
  if (!res.ok) {
    throw new ApiError(`Failed to load contract`, res.status);
  }
  return res.json();
}

export default async function ContractPage({ params }: PageProps) {
  const { id } = await params;

  let contract: ContractDetail;
  try {
    contract = await fetchContract(id);
  } catch (err) {
    return (
      <div className="border-destructive/40 bg-destructive/5 rounded-sm border px-4 py-6">
        <p className="text-caption text-destructive mb-2 font-mono uppercase">
          Couldn&rsquo;t load contract
        </p>
        <p className="text-body-sm text-foreground">
          {err instanceof ApiError
            ? `Backend returned ${err.status}.`
            : "Something went wrong reaching the analysis server."}
        </p>
        <Link
          href="/dashboard"
          className="text-body-sm text-foreground mt-4 inline-block underline underline-offset-4"
        >
          Back to dashboard
        </Link>
      </div>
    );
  }

  return <ContractDetailView contract={contract} />;
}
