import { SectionHeader } from "@/components/ui/section-header";

export function Provenance() {
  return (
    <section
      id="provenance"
      className="border-border/50 relative scroll-mt-20 border-t px-6 py-32 pl-14 md:px-10 md:py-40 md:pl-24 lg:py-48 xl:py-56 xl:pl-28"
    >
      <div className="gap-loose mx-auto grid w-full max-w-[1200px] grid-cols-1 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-20">
        <div>
          <SectionHeader number="004" label="On provenance" className="mb-loose" />

          <div className="flex items-baseline gap-4">
            <span className="font-display text-display-md text-foreground font-medium">30%</span>
            <span className="text-caption text-muted-foreground font-mono uppercase">
              to <span className="text-foreground">50%</span>
            </span>
          </div>
          <p className="mt-tight text-body-sm text-muted-foreground max-w-xs">
            of clauses analyzed are recognized from a shared cache. The rest are analyzed fresh,
            embedded, and contributed back.
          </p>
        </div>

        <div>
          <p className="font-editorial text-display-lg text-foreground leading-[1.2]">
            &ldquo;ClauseGuard isn&apos;t a lawyer. It&apos;s a tool that reads carefully, remembers
            what it&apos;s seen, and shows its work.&rdquo;
          </p>
          <p className="mt-normal text-body-lg text-muted-foreground">
            Every clause is compared against market-standard templates in a vector index. Risk is
            explained with citations to comparable language. Confidence is reported honestly. When
            the model is uncertain, the clause is flagged as such rather than guessed. For
            consequential agreements, get a lawyer. For everything else, get a second opinion in
            sixty seconds.
          </p>
          <p className="mt-normal text-caption text-muted-foreground flex flex-wrap items-center gap-x-3 gap-y-2 font-mono uppercase">
            <span className="text-foreground">Evidence-first</span>
            <span aria-hidden className="bg-border h-px w-4" />
            <span>Transparent confidence</span>
            <span aria-hidden className="bg-border h-px w-4" />
            <span>Not legal advice</span>
          </p>
        </div>
      </div>
    </section>
  );
}
