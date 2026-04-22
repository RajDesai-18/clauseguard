import type { ReactNode } from "react";

export type ContractStatus =
  | "queued"
  | "parsing"
  | "analyzing"
  | "scoring"
  | "complete"
  | "failed";

const PROCESSING: ContractStatus[] = ["queued", "parsing", "analyzing", "scoring"];

const LABELS: Record<ContractStatus, string> = {
  queued: "Queued",
  parsing: "Parsing",
  analyzing: "Analyzing",
  scoring: "Scoring",
  complete: "Complete",
  failed: "Failed",
};

export function StatusBadge({ status }: { status: ContractStatus }): ReactNode {
  const isProcessing = PROCESSING.includes(status);
  const isFailed = status === "failed";

  return (
    <span
      className={`text-caption inline-flex items-center gap-1.5 font-mono uppercase ${
        isFailed
          ? "text-destructive"
          : isProcessing
            ? "text-foreground"
            : "text-muted-foreground"
      }`}
    >
      {isProcessing && (
        <span
          aria-hidden
          className="bg-foreground size-1.5 animate-pulse rounded-full"
        />
      )}
      {LABELS[status]}
    </span>
  );
}