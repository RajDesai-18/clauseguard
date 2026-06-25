import { notFound } from "next/navigation";
import Link from "next/link";
import { ContractDetailView } from "@/components/features/contract-detail-view";
import { ErrorState } from "@/components/system/error-state";
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

    const message =
      err instanceof ApiError ? err.message : "Something went wrong reaching the analysis server.";
    const requestId = err instanceof ApiError ? err.requestId : undefined;

    return (
      <ErrorState
        title="Couldn't load contract"
        message={message}
        requestId={requestId}
        action={
          <Link
            href="/dashboard"
            className="text-body-sm text-foreground inline-block underline underline-offset-4"
          >
            Back to dashboard
          </Link>
        }
      />
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
