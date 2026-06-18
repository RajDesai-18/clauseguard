"use client";

import Link from "next/link";
import { ArrowLeft, Download } from "lucide-react";
import { useEffect, useState } from "react";
import { RiskPill } from "@/components/ui/risk-pill";
import { StatusBadge } from "@/components/ui/status-badge";
import { ClauseList } from "@/components/contract/clause-list";
import type { ContractStatus } from "@/components/ui/status-badge";
import type { StreamStatus } from "@/lib/hooks/use-contract-stream";
import { ProgressTracker } from "@/components/features/progress-tracker";
import { getContractClient, type ClauseDetail } from "@/lib/api/api-client";

const PROCESSING_STATUSES: ContractStatus[] = ["queued", "parsing", "analyzing", "scoring"];

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
}

interface Props {
  contract: Contract;
  clauses: ClauseDetail[];
}

export function ContractDetailView({ contract: initialContract, clauses }: Props) {
  const [status, setStatus] = useState<ContractStatus>(initialContract.status as ContractStatus);
  const [contract, setContract] = useState(initialContract);
  const isProcessing = PROCESSING_STATUSES.includes(status);

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

  return (
    <div className="space-y-12">
      <section className="border-border/40 bg-card space-y-6 rounded-sm border p-6">
        <div>
          <p className="text-body-sm text-muted-foreground mb-2 font-mono uppercase">
            Analysis complete
          </p>
          <h3 className="text-heading-md font-display text-foreground font-medium">
            {contract.clause_count} clauses analyzed
          </h3>
        </div>

        {contract.summary && (
          <div>
            <p className="text-body-sm text-muted-foreground mb-2 font-mono uppercase">Summary</p>
            <p className="text-body text-foreground">{contract.summary}</p>
          </div>
        )}
      </section>

      <ClauseList clauses={clauses} />
    </div>
  );
}
