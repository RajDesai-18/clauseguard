import Link from "next/link";

import { Dossier } from "@/components/dashboard/dossier";
import { listContracts, ApiError } from "@/lib/api/api-client";
import type { ContractSummary } from "@/lib/api/api-client";

export default async function DashboardPage() {
  let contracts: ContractSummary[] = [];
  let fetchError: string | null = null;

  try {
    const response = await listContracts({ size: 50 });
    contracts = response.items;
  } catch (err) {
    // The (app) layout guarantees a session, so 401 here would only
    // mean session expired between the layout check and this fetch.
    // Treat all errors uniformly as a connection problem; the user can
    // refresh, which will re-trigger the layout's session check.
    fetchError =
      err instanceof ApiError
        ? `Couldn't reach the analysis server (${err.status}).`
        : "Couldn't reach the analysis server.";
  }

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

      {fetchError ? <ErrorState message={fetchError} /> : <Dossier initialContracts={contracts} />}
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
