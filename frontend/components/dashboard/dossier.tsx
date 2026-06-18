"use client";

import Link from "next/link";
import { useState } from "react";
import { MoreVertical } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { RiskPill } from "@/components/ui/risk-pill";
import { StatusBadge } from "@/components/ui/status-badge";

import { ApiError, deleteContract } from "@/lib/api/api-client";
import type { ContractSummary } from "@/lib/api/api-client";
import { formatRelativeDate } from "@/lib/mock-contracts";

const PROCESSING_STATUSES = ["queued", "parsing", "analyzing", "scoring"];

/**
 * The interactive piece of the dashboard. Owns the contracts list
 * state so that delete mutations update the summary stats, the
 * table, and the empty-state in lockstep, without a full page
 * refresh. The Server Component passes the initial fetch result in
 * as `initialContracts`; we keep that snapshot around for
 * restore-on-failure if a delete request errors out.
 */
export function Dossier({ initialContracts }: { initialContracts: ContractSummary[] }) {
  const [contracts, setContracts] = useState(initialContracts);
  const [pendingDelete, setPendingDelete] = useState<ContractSummary | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Derived stats — recompute every render, cheap for any realistic list size.
  const total = contracts.length;
  const highRisk = contracts.filter((c) => c.overall_risk === "high").length;
  const processing = contracts.filter((c) => PROCESSING_STATUSES.includes(c.status)).length;

  const handleDeleteRequest = (contract: ContractSummary) => {
    setPendingDelete(contract);
    setDeleteError(null);
  };

  const handleDeleteCancel = () => {
    if (isDeleting) return;
    setPendingDelete(null);
    setDeleteError(null);
  };

  const handleDeleteConfirm = async () => {
    if (!pendingDelete) return;

    const target = pendingDelete;
    setIsDeleting(true);
    setDeleteError(null);

    // Optimistic removal — drop the row immediately for a snappy feel.
    setContracts((prev) => prev.filter((c) => c.id !== target.id));

    try {
      await deleteContract(target.id);
      setPendingDelete(null);
    } catch (err) {
      // Restore the row at its original position from the props snapshot.
      setContracts((prev) => {
        const originalIndex = initialContracts.findIndex((c) => c.id === target.id);
        if (originalIndex < 0) return [...prev, target];
        const next = [...prev];
        next.splice(originalIndex, 0, target);
        return next;
      });
      setDeleteError(
        err instanceof ApiError
          ? `Couldn't delete the contract (${err.status}).`
          : "Couldn't delete the contract. Please try again."
      );
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <>
      <section
        aria-label="Summary"
        className="border-border/40 grid grid-cols-1 gap-0 border-y sm:grid-cols-3"
      >
        <StatCard label="Total contracts" value={String(total)} />
        <StatCard
          label="High risk"
          value={String(highRisk)}
          accent={highRisk > 0 ? "risk-high" : undefined}
        />
        <StatCard label="In progress" value={String(processing)} />
      </section>

      <section aria-label="Contract list">
        {contracts.length === 0 ? (
          <EmptyState />
        ) : (
          <ContractTable contracts={contracts} onDeleteRequest={handleDeleteRequest} />
        )}
      </section>

      <Dialog
        open={pendingDelete !== null}
        onOpenChange={(open) => {
          if (!open) handleDeleteCancel();
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-display text-heading-md font-medium">
              Delete contract?
            </DialogTitle>
            <DialogDescription className="text-body text-muted-foreground mt-2 leading-relaxed">
              This will permanently delete{" "}
              <span className="text-foreground font-medium">{pendingDelete?.file_name}</span> and
              all of its analysis. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>

          {deleteError && (
            <div className="border-destructive/40 bg-destructive/5 text-destructive mt-2 rounded-sm border px-3 py-2 text-[13px]">
              {deleteError}
            </div>
          )}

          <DialogFooter className="mt-6 gap-2">
            <button
              type="button"
              onClick={handleDeleteCancel}
              disabled={isDeleting}
              className="border-border bg-card hover:bg-foreground/4 hover:border-border/80 focus-visible:border-foreground focus-visible:ring-foreground/30 focus-visible:bg-foreground/4 text-foreground/90 hover:text-foreground focus-visible:text-foreground inline-flex items-center justify-center rounded-sm border px-4 py-2 font-mono text-[11px] tracking-[0.08em] uppercase transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-offset-0 focus-visible:outline-none disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleDeleteConfirm}
              disabled={isDeleting}
              className="bg-risk-high text-background hover:bg-risk-high/90 focus-visible:ring-risk-high/40 inline-flex items-center justify-center rounded-sm border border-transparent px-4 py-2 font-mono text-[11px] tracking-[0.08em] uppercase transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-offset-0 focus-visible:outline-none disabled:opacity-60"
            >
              {isDeleting ? "Deleting…" : "Delete contract"}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: "risk-high";
}) {
  return (
    <div className="border-border/40 px-1 py-6 first:pl-0 sm:border-l sm:px-6 sm:first:border-l-0">
      <p className="text-caption text-muted-foreground font-mono uppercase">{label}</p>
      <p
        className={`font-display text-display-lg mt-2 font-medium tracking-[-0.028em] ${
          accent === "risk-high" ? "text-risk-high" : "text-foreground"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

function ContractTable({
  contracts,
  onDeleteRequest,
}: {
  contracts: ContractSummary[];
  onDeleteRequest: (contract: ContractSummary) => void;
}) {
  return (
    <div className="border-border/40 border-y">
      <table className="w-full">
        <thead>
          <tr className="border-border/40 border-b">
            <Th>File</Th>
            <Th className="hidden md:table-cell">Type</Th>
            <Th>Status</Th>
            <Th>Risk</Th>
            <Th className="hidden sm:table-cell">Clauses</Th>
            <Th className="hidden lg:table-cell">Uploaded</Th>
            <Th className="w-12">
              <span className="sr-only">Actions</span>
            </Th>
          </tr>
        </thead>
        <tbody>
          {contracts.map((c) => (
            <ContractRow key={c.id} contract={c} onDeleteRequest={() => onDeleteRequest(c)} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Th({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <th
      scope="col"
      className={`text-caption text-muted-foreground px-4 py-3 text-left font-mono font-normal uppercase ${className}`}
    >
      {children}
    </th>
  );
}

function ContractRow({
  contract,
  onDeleteRequest,
}: {
  contract: ContractSummary;
  onDeleteRequest: () => void;
}) {
  return (
    <tr className="border-border/40 group hover:bg-muted/60 ease-out-strong relative border-b transition-colors duration-150 last:border-b-0">
      <td className="relative px-4 py-4">
        <span
          aria-hidden
          className="bg-foreground ease-out-strong absolute inset-y-2 left-0 w-0.5 origin-top scale-y-0 transition-transform duration-150 group-hover:scale-y-100"
        />
        <Link
          href={`/contract/${contract.id}`}
          className="text-body-sm text-foreground/85 group-hover:text-foreground ease-out-strong block font-medium transition-colors duration-150"
        >
          {contract.file_name}
        </Link>
      </td>
      <td className="text-body-sm text-muted-foreground hidden px-4 py-4 md:table-cell">
        {contract.contract_type ?? "—"}
      </td>
      <td className="px-4 py-4">
        <StatusBadge status={contract.status} />
      </td>
      <td className="px-4 py-4">
        {contract.overall_risk ? (
          <RiskPill level={contract.overall_risk} />
        ) : (
          <span className="text-muted-foreground/60 text-caption font-mono">—</span>
        )}
      </td>
      <td className="text-body-sm text-muted-foreground hidden px-4 py-4 font-mono sm:table-cell">
        {contract.clause_count > 0 ? contract.clause_count : "—"}
      </td>
      <td className="text-body-sm text-muted-foreground hidden px-4 py-4 lg:table-cell">
        {formatRelativeDate(contract.created_at)}
      </td>
      <td className="px-2 py-4 text-right">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              aria-label={`Actions for ${contract.file_name}`}
              className="text-muted-foreground/60 hover:text-foreground hover:bg-foreground/4 focus-visible:bg-foreground/4 focus-visible:text-foreground focus-visible:ring-foreground/30 inline-flex h-7 w-7 items-center justify-center rounded-sm transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-offset-0 focus-visible:outline-none"
            >
              <MoreVertical className="size-4" strokeWidth={1.5} aria-hidden />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-44">
            <DropdownMenuItem
              onSelect={onDeleteRequest}
              className="text-risk-high focus:bg-risk-high/8 focus:text-risk-high cursor-pointer font-mono text-[11px] tracking-[0.08em] uppercase"
            >
              Delete contract
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </td>
    </tr>
  );
}

function EmptyState() {
  return (
    <div className="border-border/40 flex flex-col items-center justify-center rounded-sm border py-20 text-center">
      <p className="text-caption text-muted-foreground mb-4 font-mono uppercase">
        No contracts yet
      </p>
      <h3 className="text-heading-lg font-display text-foreground mb-3 font-medium">
        Your dossier is <span className="font-editorial">empty</span>
      </h3>
      <p className="text-body text-muted-foreground mb-8 max-w-[44ch]">
        Upload a PDF or DOCX and ClauseGuard will return a clause-by-clause risk breakdown in under
        a minute.
      </p>
      <Link
        href="/upload"
        className="border-foreground bg-foreground text-background hover:bg-foreground/90 font-display ease-out-strong rounded-sm border px-5 py-2.5 text-[14px] font-medium transition-colors duration-200 active:scale-[0.99]"
      >
        Upload your first contract
      </Link>
    </div>
  );
}
