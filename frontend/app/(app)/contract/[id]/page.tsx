import { notFound } from "next/navigation";
import Link from "next/link";
import { ContractDetailView } from "@/components/features/contract-detail-view";
import {
  ApiError,
  getContract,
  listClauses,
  type ClauseDetail,
  type ContractDetail,
} from "@/lib/api/api-client";

interface PageProps {
  params: Promise<{ id: string }>;
}

const TERMINAL_STATUSES = new Set(["complete", "failed"]);

export default async function ContractPage({ params }: PageProps) {
  const { id } = await params;

  let contract: ContractDetail;
  try {
    contract = await getContract(id);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) {
      notFound();
    }
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

  // Only fetch clauses for terminal contracts. In-flight contracts
  // render the SSE progress tracker and don't need clause data yet;
  // the user reloads (or navigates back) once analysis completes.
  let clauses: ClauseDetail[] = [];
  if (TERMINAL_STATUSES.has(contract.status)) {
    try {
      const clauseResponse = await listClauses(id);
      clauses = clauseResponse.clauses;
    } catch {
      // Render the contract header anyway. The detail view will show
      // an empty-clauses state, which is also what mid-pipeline
      // contracts produce. Users can refresh to retry.
    }
  }

  return <ContractDetailView contract={contract} clauses={clauses} />;
}
