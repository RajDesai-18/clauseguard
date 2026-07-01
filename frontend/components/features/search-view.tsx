"use client";

import Link from "next/link";
import { useState } from "react";
import { Search } from "lucide-react";

import { RiskPill } from "@/components/ui/risk-pill";
import { ErrorState } from "@/components/system/error-state";
import { ApiError, UnauthorizedError, searchClausesClient } from "@/lib/api/api-client";
import type {
  ClauseRiskLevel,
  SearchContractGroup,
  SearchHit,
  SearchResponse,
} from "@/lib/api/api-client";

const EXAMPLES = [
  "unlimited liability",
  "auto-renewal",
  "termination for convenience",
  "who owns the IP",
];

const MIN_QUERY_LENGTH = 2;

type SearchErr = { message: string; requestId?: string };

export function SearchView() {
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState<string | null>(null);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<SearchErr | null>(null);

  const runSearch = async (raw: string) => {
    const q = raw.trim();
    if (q.length < MIN_QUERY_LENGTH) return;

    setLoading(true);
    setError(null);
    setSubmitted(q);

    try {
      const res = await searchClausesClient(q);
      setResults(res);
    } catch (err) {
      setResults(null);
      if (err instanceof UnauthorizedError) {
        setError({ message: "Your session has expired. Refresh the page to sign in again." });
      } else if (err instanceof ApiError) {
        setError({ message: err.message, requestId: err.requestId });
      } else {
        setError({ message: "Search failed. Please try again." });
      }
    } finally {
      setLoading(false);
    }
  };

  const pickExample = (example: string) => {
    setQuery(example);
    void runSearch(example);
  };

  return (
    <div className="space-y-10">
      <header>
        <p className="text-caption text-muted-foreground mb-3 font-mono uppercase">Search</p>
        <h2 className="text-heading-lg font-display text-foreground font-medium">
          Search across <span className="font-editorial">every</span> contract
        </h2>
        <p className="text-body text-muted-foreground mt-2 max-w-[60ch]">
          Ask in plain English. ClauseGuard matches the meaning of your query against every analyzed
          clause in your dossier, not just the keywords.
        </p>
      </header>

      <div className="relative">
        <Search
          className="text-muted-foreground/60 pointer-events-none absolute top-1/2 left-4 size-4 -translate-y-1/2"
          strokeWidth={1.5}
          aria-hidden
        />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void runSearch(query);
          }}
          placeholder="Search clauses by meaning… e.g. unlimited liability"
          aria-label="Search contracts"
          autoFocus
          className="border-border bg-card text-foreground placeholder:text-muted-foreground/60 focus-visible:border-foreground focus-visible:ring-foreground/30 w-full rounded-sm border py-3.5 pr-28 pl-11 text-[15px] transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-offset-0 focus-visible:outline-none"
        />
        <button
          type="button"
          onClick={() => void runSearch(query)}
          disabled={query.trim().length < MIN_QUERY_LENGTH || loading}
          className="border-foreground bg-foreground text-background hover:bg-foreground/90 font-display absolute top-1/2 right-2 -translate-y-1/2 rounded-sm border px-4 py-2 text-[13px] font-medium transition-colors duration-150 active:scale-[0.99] disabled:opacity-40"
        >
          Search
        </button>
      </div>

      {loading ? (
        <SearchSkeleton />
      ) : error ? (
        <ErrorState
          title="Search failed"
          message={error.message}
          requestId={error.requestId}
          action={
            submitted ? (
              <button
                type="button"
                onClick={() => void runSearch(submitted)}
                className="border-border bg-card hover:bg-foreground/4 hover:border-border/80 text-foreground/90 hover:text-foreground inline-flex items-center rounded-sm border px-4 py-2 font-mono text-[11px] tracking-[0.08em] uppercase transition-colors duration-150"
              >
                Try again
              </button>
            ) : undefined
          }
        />
      ) : submitted === null ? (
        <ExamplePrompts onPick={pickExample} />
      ) : results && results.total_hits === 0 ? (
        <NoResults query={submitted} />
      ) : results ? (
        <Results results={results} />
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Results
// ---------------------------------------------------------------------------

function Results({ results }: { results: SearchResponse }) {
  // Normalize relevance bars to the strongest hit across the whole response,
  // so the best match reads as full and the weaker tail reads as shorter.
  const maxSimilarity = results.groups.reduce((m, g) => Math.max(m, g.top_similarity), 0) || 1;

  return (
    <div className="space-y-10">
      <p className="text-caption text-muted-foreground font-mono uppercase">
        {results.total_hits} {plural(results.total_hits, "match", "matches")} across{" "}
        {results.groups.length} {plural(results.groups.length, "contract", "contracts")}
      </p>

      {results.groups.map((group) => (
        <Group key={group.contract_id} group={group} maxSimilarity={maxSimilarity} />
      ))}
    </div>
  );
}

function Group({ group, maxSimilarity }: { group: SearchContractGroup; maxSimilarity: number }) {
  return (
    <section aria-label={group.file_name} className="space-y-3">
      <header className="border-border/40 flex items-baseline justify-between gap-4 border-b pb-3">
        <div className="min-w-0">
          <Link
            href={`/contract/${group.contract_id}`}
            className="text-foreground hover:text-foreground/75 font-display ease-out-strong text-[19px] font-medium tracking-[-0.01em] transition-colors duration-150"
          >
            {group.file_name}
          </Link>
          <div className="mt-1.5 flex items-center gap-2.5">
            {group.contract_type && (
              <span className="text-caption text-muted-foreground font-mono uppercase">
                {group.contract_type}
              </span>
            )}
            {group.overall_risk && <RiskPill level={group.overall_risk} />}
          </div>
        </div>
        <span className="text-caption text-muted-foreground shrink-0 font-mono uppercase">
          {group.hits.length} {plural(group.hits.length, "match", "matches")}
        </span>
      </header>

      <div className="space-y-2">
        {group.hits.map((hit) => (
          <HitCard
            key={hit.clause_id}
            hit={hit}
            contractId={group.contract_id}
            maxSimilarity={maxSimilarity}
          />
        ))}
      </div>
    </section>
  );
}

const RISK_SPINE: Record<ClauseRiskLevel, string> = {
  green: "border-l-risk-low",
  yellow: "border-l-risk-med",
  red: "border-l-risk-high",
};

function HitCard({
  hit,
  contractId,
  maxSimilarity,
}: {
  hit: SearchHit;
  contractId: string;
  maxSimilarity: number;
}) {
  const headline = firstSentence(hit.explanation);
  const snippet = snippetOf(hit.original_text);

  return (
    <Link
      href={`/contract/${contractId}`}
      className={`group ease-out-strong bg-card hover:bg-card/70 block rounded-r-sm border-l-2 py-3.5 pr-4 pl-4 transition-colors duration-150 ${RISK_SPINE[hit.risk_level]}`}
    >
      <div className="flex items-baseline justify-between gap-4">
        <p className="text-caption text-muted-foreground font-mono tracking-[0.08em] uppercase">
          {formatClauseType(hit.clause_type)}
        </p>
        <RelevanceBar value={hit.similarity} max={maxSimilarity} />
      </div>
      {headline && (
        <p className="text-foreground mt-2 text-[15px] leading-[1.6] font-medium">{headline}</p>
      )}
      <p className="text-muted-foreground mt-1.5 text-[13.5px] leading-[1.6]">{snippet}</p>
    </Link>
  );
}

function RelevanceBar({ value, max }: { value: number; max: number }) {
  const pct = Math.max(8, Math.min(100, (value / max) * 100));
  return (
    <span
      className="inline-flex shrink-0 items-center"
      title={`Relevance ${value.toFixed(2)}`}
      aria-hidden
    >
      <span className="bg-border/60 relative block h-1 w-16 overflow-hidden rounded-full">
        <span
          className="bg-foreground/70 absolute inset-y-0 left-0 rounded-full"
          style={{ width: `${pct}%` }}
        />
      </span>
    </span>
  );
}

// ---------------------------------------------------------------------------
// Empty / prompt / loading states
// ---------------------------------------------------------------------------

function ExamplePrompts({ onPick }: { onPick: (example: string) => void }) {
  return (
    <div className="space-y-4">
      <p className="text-caption text-muted-foreground font-mono uppercase">Try</p>
      <div className="flex flex-wrap gap-2">
        {EXAMPLES.map((example) => (
          <button
            key={example}
            type="button"
            onClick={() => onPick(example)}
            className="border-border bg-card hover:bg-foreground/4 hover:border-border/80 text-foreground/80 hover:text-foreground ease-out-strong rounded-sm border px-3 py-1.5 text-[13px] transition-colors duration-150"
          >
            {example}
          </button>
        ))}
      </div>
    </div>
  );
}

function NoResults({ query }: { query: string }) {
  return (
    <div className="border-border/40 flex flex-col items-center justify-center rounded-sm border py-16 text-center">
      <p className="text-caption text-muted-foreground mb-3 font-mono uppercase">No matches</p>
      <h3 className="text-heading-md font-display text-foreground mb-2 font-medium">
        Nothing turned up for &ldquo;{query}&rdquo;
      </h3>
      <p className="text-body text-muted-foreground max-w-[46ch]">
        Try broader wording or a concept rather than exact contract language. Search matches
        meaning, so a plain-English phrase often works better than a quote.
      </p>
    </div>
  );
}

function SearchSkeleton() {
  return (
    <div className="space-y-4" aria-hidden>
      <p className="text-caption text-muted-foreground animate-pulse font-mono uppercase">
        Searching…
      </p>
      <div className="space-y-2">
        {[0, 1, 2].map((i) => (
          <div key={i} className="border-border/40 bg-card h-20 animate-pulse rounded-sm border" />
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function plural(n: number, one: string, many: string): string {
  return n === 1 ? one : many;
}

function formatClauseType(snake: string): string {
  return snake
    .split("_")
    .map((w) => (w.length === 0 ? w : w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()))
    .join(" ");
}

function firstSentence(text: string, max = 200): string {
  const clean = text.trim().replace(/\s+/g, " ");
  const match = clean.match(/^[^.!?]+[.!?]/);
  const sentence = match ? match[0].trim() : clean;
  return sentence.length > max ? sentence.slice(0, max).trimEnd() + "\u2026" : sentence;
}

function snippetOf(text: string, max = 180): string {
  const clean = text.trim().replace(/\s+/g, " ");
  return clean.length > max ? clean.slice(0, max).trimEnd() + "\u2026" : clean;
}
