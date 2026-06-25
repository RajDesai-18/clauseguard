"use client";

import Link from "next/link";
import { ArrowLeft, Download, TriangleAlert } from "lucide-react";
import { useEffect, useState } from "react";
import { RiskPill } from "@/components/ui/risk-pill";
import { StatusBadge } from "@/components/ui/status-badge";
import { ClauseList } from "@/components/contract/clause-list";
import type { ContractStatus } from "@/components/ui/status-badge";
import type { StreamStatus } from "@/lib/hooks/use-contract-stream";
import { ProgressTracker } from "@/components/features/progress-tracker";
import { getContractClient, listClausesClient, type ClauseDetail } from "@/lib/api/api-client";

const PROCESSING_STATUSES: ContractStatus[] = ["queued", "parsing", "analyzing", "scoring"];

// How many times to re-poll clauses when a contract completes but the
// finalize step hasn't flushed clause rows yet, and how long to wait
// between attempts. Bounded so a genuinely clause-less contract (e.g. a
// degraded one) doesn't poll forever.
const CLAUSE_REFETCH_ATTEMPTS = 4;
const CLAUSE_REFETCH_DELAY_MS = 800;

interface Contract {
  id: string;
  file_name: string;
  contract_type: string | null;
  status: string;
  overall_risk: "low" | "medium" | "high" | null;
  clause_count: number;
  created_at: string;
  analyzed_at: string | null;
  summary: string | null;
  degraded_reason: string | null;
}

interface Props {
  contract: Contract;
  clauses: ClauseDetail[];
}

export function ContractDetailView({ contract: initialContract, clauses: initialClauses }: Props) {
  const [status, setStatus] = useState<ContractStatus>(initialContract.status as ContractStatus);
  const [contract, setContract] = useState(initialContract);
  const [clauses, setClauses] = useState(initialClauses);
  const isProcessing = PROCESSING_STATUSES.includes(status);

  // When the contract reaches a terminal status (typically via SSE while
  // the user watches), refetch the contract record so summary/risk/
  // degraded_reason reflect the final state.
  useEffect(() => {
    if (isProcessing) return;
    if (status === contract.status) return;

    let cancelled = false;

    getContractClient(initialContract.id)
      .then((data) => {
        if (!cancelled) setContract(data);
      })
      .catch(() => {
        // Silent: page already shows initial data. Refresh to retry.
      });

    return () => {
      cancelled = true;
    };
  }, [isProcessing, status, contract.status, initialContract.id]);

  // Refetch clauses when the contract completes with none loaded.
  //
  // On a fresh upload the page first renders mid-pipeline with zero
  // clauses. When SSE flips status to "complete", the server-fetched
  // clause prop is stale (empty). We refetch client-side, with a short
  // bounded retry to cover the brief window where finalize hasn't
  // flushed clause rows yet. Degraded and failed contracts are skipped:
  // zero clauses is their correct terminal state, so polling is wasted.
  useEffect(() => {
    if (status !== "complete") return;
    if (clauses.length > 0) return;
    if (contract.degraded_reason !== null) return;

    let cancelled = false;

    const poll = async (attempt: number): Promise<void> => {
      try {
        const res = await listClausesClient(initialContract.id);
        if (cancelled) return;

        if (res.clauses.length > 0) {
          setClauses(res.clauses);
          return;
        }
      } catch {
        // Treat a fetch error like an empty result: fall through to retry
        // or give up. The page stays usable either way.
      }

      if (!cancelled && attempt < CLAUSE_REFETCH_ATTEMPTS) {
        setTimeout(() => {
          if (!cancelled) void poll(attempt + 1);
        }, CLAUSE_REFETCH_DELAY_MS);
      }
    };

    void poll(1);

    return () => {
      cancelled = true;
    };
  }, [status, clauses.length, contract.degraded_reason, initialContract.id]);

  const handleStreamStatusChange = (next: StreamStatus) => {
    if (
      next === "queued" ||
      next === "parsing" ||
      next === "analyzing" ||
      next === "scoring" ||
      next === "complete" ||
      next === "failed"
    ) {
      setStatus(next);
    }
  };

  return (
    <div className="space-y-12">
      <header className="space-y-4">
        <Link
          href="/dashboard"
          className="text-caption text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 font-mono uppercase transition-colors duration-150 ease-[cubic-bezier(0.23,1,0.32,1)]"
        >
          <ArrowLeft className="size-3.5" strokeWidth={1.5} />
          Dashboard
        </Link>

        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-caption text-muted-foreground mb-2 font-mono uppercase">Contract</p>
            <h2 className="text-heading-lg font-display text-foreground font-medium break-all">
              {contract.file_name}
            </h2>
            <div className="mt-3 flex flex-wrap items-center gap-4">
              <StatusBadge status={status} />
              {contract.overall_risk && <RiskPill level={contract.overall_risk} />}
              {contract.contract_type && (
                <span className="text-caption text-muted-foreground font-mono uppercase">
                  {contract.contract_type}
                </span>
              )}
            </div>
          </div>
          {status === "complete" && (
            <a
              href={`/api/contracts/${initialContract.id}/export`}
              download
              className="border-border bg-card hover:bg-foreground/4 hover:border-border/80 focus-visible:border-foreground focus-visible:ring-foreground/30 focus-visible:bg-foreground/4 text-foreground/90 hover:text-foreground focus-visible:text-foreground inline-flex items-center gap-2 rounded-sm border px-3 py-2 font-mono text-[11px] tracking-[0.08em] uppercase transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-offset-0 focus-visible:outline-none"
            >
              <Download className="size-3.5" strokeWidth={1.5} aria-hidden />
              Download review
            </a>
          )}
        </div>
      </header>

      {isProcessing ? (
        <ProgressTracker
          contractId={initialContract.id}
          onStatusChange={handleStreamStatusChange}
        />
      ) : (
        <CompletionView contract={contract} clauses={clauses} />
      )}
    </div>
  );
}

function CompletionView({ contract, clauses }: { contract: Contract; clauses: ClauseDetail[] }) {
  if (contract.status === "failed") {
    return (
      <div className="border-destructive/40 bg-destructive/5 rounded-sm border px-6 py-8">
        <p className="text-caption text-destructive mb-2 font-mono uppercase">Analysis failed</p>
        <p className="text-body text-foreground">
          The pipeline didn&rsquo;t complete for this contract. The file is still stored and we can
          retry it in a future session.
        </p>
      </div>
    );
  }

  const isDegraded = contract.degraded_reason !== null;

  // Tier 1 degradation: the document was parsed but never split into
  // clauses (LLM was down at split time), so there is nothing to list.
  // Show the banner alone rather than an empty clause section.
  const hasClauses = clauses.length > 0;

  return (
    <div className="space-y-12">
      {isDegraded && <DegradedBanner reason={contract.degraded_reason as string} />}

      <section className="border-border/40 bg-card space-y-6 rounded-sm border p-6">
        <div>
          <p className="text-body-sm text-muted-foreground mb-2 font-mono uppercase">
            {isDegraded ? "Document saved" : "Analysis complete"}
          </p>
          <h3 className="text-heading-md font-display text-foreground font-medium">
            {hasClauses
              ? `${contract.clause_count} clauses analyzed`
              : "Document parsed without analysis"}
          </h3>
        </div>

        {contract.summary && (
          <div>
            <p className="text-body-sm text-muted-foreground mb-2 font-mono uppercase">Summary</p>
            <p className="text-body text-foreground">{contract.summary}</p>
          </div>
        )}
      </section>

      {hasClauses && <ClauseList clauses={clauses} />}
    </div>
  );
}

function DegradedBanner({ reason }: { reason: string }) {
  return (
    <div
      role="status"
      className="border-risk-medium/40 bg-risk-medium/5 rounded-sm border px-6 py-5"
    >
      <div className="flex items-start gap-3">
        <TriangleAlert
          className="text-risk-medium mt-0.5 size-4 shrink-0"
          strokeWidth={1.5}
          aria-hidden
        />
        <div className="space-y-1.5">
          <p className="text-caption text-risk-medium font-mono uppercase">
            AI analysis unavailable
          </p>
          <p className="text-body text-foreground/90 leading-relaxed">{reason}</p>
        </div>
      </div>
    </div>
  );
}
