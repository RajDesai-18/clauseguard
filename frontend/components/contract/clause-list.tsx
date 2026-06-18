import { ClauseCard } from "./clause-card";
import type { ClauseDetail } from "@/lib/api/api-client";

interface Props {
  clauses: ClauseDetail[];
}

/**
 * Container for the annotated review. Flush-left layout matches the
 * analysis card above; dedupes by trimmed text content (the Bonterms
 * parser picks up the publisher disclaimer at positions 13 and 17),
 * and sorts by document position.
 */
export function ClauseList({ clauses }: Props) {
  const seen = new Set<string>();
  const unique = clauses.filter((c) => {
    const key = c.original_text.trim();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  const sorted = [...unique].sort((a, b) => a.position - b.position);

  if (sorted.length === 0) {
    return (
      <section className="border-border/40 mx-auto rounded-sm border border-dashed p-6">
        <p className="text-caption text-muted-foreground font-mono uppercase tracking-[0.08em]">
          No clauses
        </p>
        <p className="text-body text-foreground mt-2">
          We didn&rsquo;t extract any clauses from this document. The file may have been empty or
          in an unexpected format.
        </p>
      </section>
    );
  }

  return (
    <section className="mx-auto">
      <header className="mb-14 space-y-2">
        <p className="text-body text-muted-foreground font-mono uppercase tracking-[0.08em]">
          Annotated review
        </p>
        <p className="text-muted-foreground text-[14px] leading-[1.65]">
          Read through. Anything to watch is flagged inline.
        </p>
      </header>
      <div className="space-y-14">
        {sorted.map((clause) => (
          <ClauseCard key={clause.id} clause={clause} />
        ))}
      </div>
    </section>
  );
}