import { Search } from "lucide-react";

export const metadata = {
  title: "Search",
};

/**
 * STUB (Phase 7): cross-contract semantic clause search.
 *
 * Placeholder route so the rail's Search item resolves. The real build
 * uses the pgvector embeddings already generated for every clause in
 * finalize: embed the query, run a similarity search across the user's
 * clauses, group hits by source contract. See Phase 6 handoff.
 */
export default function SearchPage() {
  return (
    <div className="flex min-h-[55vh] flex-col items-center justify-center px-6 text-center">
      <div className="w-full max-w-[520px]">
        <Search
          className="text-muted-foreground/50 mx-auto size-7"
          strokeWidth={1.25}
          aria-hidden
        />
        <p className="text-caption text-muted-foreground mt-6 font-mono tracking-[0.14em] uppercase">
          Coming soon
        </p>
        <h2 className="font-display text-heading-lg text-foreground mt-4 font-medium tracking-[-0.02em]">
          Search across <span className="font-editorial">every</span> contract
        </h2>
        <p className="text-body text-muted-foreground mx-auto mt-3 max-w-[42ch] leading-relaxed">
          Ask plain-English questions across your whole dossier, &ldquo;where did I agree to
          unlimited liability?&rdquo; &ldquo;show me every auto-renewal clause&rdquo;, and jump
          straight to the source. Semantic search over your contracts is on the way.
        </p>
      </div>
    </div>
  );
}
