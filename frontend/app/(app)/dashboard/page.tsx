import Link from "next/link";
import { RiskPill } from "@/components/ui/risk-pill";
import { StatusBadge } from "@/components/ui/status-badge";
import { listContracts, ApiError } from "@/lib/api/api-client";
import type { ContractSummary } from "@/lib/api/api-client";
import { formatRelativeDate } from "@/lib/mock-contracts";

const PROCESSING_STATUSES = ["queued", "parsing", "analyzing", "scoring"];

export default async function DashboardPage() {
  let contracts: ContractSummary[] = [];
  let fetchError: string | null = null;

  try {
    const response = await listContracts({ size: 50 });
    contracts = response.items;
  } catch (err) {
    fetchError =
      err instanceof ApiError
        ? `Couldn't reach the analysis server (${err.status}).`
        : "Couldn't reach the analysis server.";
  }

  const total = contracts.length;
  const highRisk = contracts.filter((c) => c.overall_risk === "high").length;
  const processing = contracts.filter((c) => PROCESSING_STATUSES.includes(c.status)).length;

  return (
    <div className="space-y-12">
      <header className="flex items-start justify-between gap-6">
        <div>
          <p className="text-caption text-muted-foreground mb-3 font-mono uppercase">Contracts</p>
          <h2 className="text-heading-lg font-display text-foreground font-medium">Your dossier</h2>
          <p className="text-body text-muted-foreground mt-2 max-w-[60ch]">
            Every contract you&rsquo;ve uploaded, with its current risk reading and analysis status.
          </p>
        </div>
        <Link
          href="/upload"
          className="border-foreground bg-foreground text-background hover:bg-foreground/90 font-display shrink-0 rounded-sm border px-4 py-2 text-[14px] font-medium transition-colors duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] active:scale-[0.99]"
        >
          Upload contract
        </Link>
      </header>

      {fetchError ? (
        <ErrorState message={fetchError} />
      ) : (
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
            {contracts.length === 0 ? <EmptyState /> : <ContractTable contracts={contracts} />}
          </section>
        </>
      )}
    </div>
  );
}

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

function ContractTable({ contracts }: { contracts: ContractSummary[] }) {
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
          </tr>
        </thead>
        <tbody>
          {contracts.map((c) => (
            <ContractRow key={c.id} contract={c} />
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

function ContractRow({ contract }: { contract: ContractSummary }) {
  return (
    <tr className="border-border/40 group hover:bg-muted/60 relative cursor-pointer border-b transition-colors duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] last:border-b-0">
      <td className="relative px-4 py-4">
        <span
          aria-hidden
          className="bg-foreground absolute inset-y-2 left-0 w-[2px] origin-top scale-y-0 transition-transform duration-150 ease-[cubic-bezier(0.23,1,0.32,1)] group-hover:scale-y-100"
        />
        <Link
          href={`/contract/${contract.id}`}
          className="text-body-sm text-foreground/85 group-hover:text-foreground block font-medium transition-colors duration-150 ease-[cubic-bezier(0.23,1,0.32,1)]"
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
          <span className="text-muted-foreground/60 text-caption font-mono">&mdash;</span>
        )}
      </td>
      <td className="text-body-sm text-muted-foreground hidden px-4 py-4 font-mono sm:table-cell">
        {contract.clause_count > 0 ? contract.clause_count : "—"}
      </td>
      <td className="text-body-sm text-muted-foreground hidden px-4 py-4 lg:table-cell">
        {formatRelativeDate(contract.created_at)}
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
        className="border-foreground bg-foreground text-background hover:bg-foreground/90 font-display rounded-sm border px-5 py-2.5 text-[14px] font-medium transition-colors duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] active:scale-[0.99]"
      >
        Upload your first contract
      </Link>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="border-destructive/40 bg-destructive/5 flex flex-col items-center justify-center rounded-sm border py-16 text-center">
      <p className="text-caption text-destructive mb-3 font-mono uppercase">Connection error</p>
      <h3 className="text-heading-lg font-display text-foreground mb-3 font-medium">
        Something&rsquo;s off between here and the backend
      </h3>
      <p className="text-body text-muted-foreground max-w-[52ch]">{message}</p>
      <p className="text-body-sm text-muted-foreground mt-4 font-mono">
        Is <code className="bg-muted rounded-sm px-1.5 py-0.5">docker compose up</code> running?
      </p>
    </div>
  );
}
