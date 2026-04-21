import { SectionHeader } from "@/components/ui/section-header";

export function Provenance() {
    return (
        <section
            id="provenance"
            className="relative scroll-mt-20 border-t border-border/50 px-6 py-32 pl-14 md:px-10 md:py-40 md:pl-24 lg:py-48 xl:py-56 xl:pl-28"
        >
            <div className="mx-auto grid w-full max-w-[1200px] grid-cols-1 gap-loose lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-20">
                <div>
                    <SectionHeader
                        number="004"
                        label="On provenance"
                        className="mb-loose"
                    />

                    <div className="flex items-baseline gap-4">
                        <span className="font-display text-display-md font-medium text-foreground">
                            30%
                        </span>
                        <span className="font-mono text-caption uppercase text-muted-foreground">
                            to <span className="text-foreground">50%</span>
                        </span>
                    </div>
                    <p className="mt-tight max-w-xs text-body-sm text-muted-foreground">
                        of clauses analyzed are recognized from a shared cache. The rest
                        are analyzed fresh, embedded, and contributed back.
                    </p>
                </div>

                <div>
                    <p className="font-editorial text-display-lg leading-[1.2] text-foreground">
                        &ldquo;ClauseGuard isn&apos;t a lawyer. It&apos;s a tool that reads
                        carefully, remembers what it&apos;s seen, and shows its work.&rdquo;
                    </p>
                    <p className="mt-normal text-body-lg text-muted-foreground">
                        Every clause is compared against market-standard templates in a
                        vector index. Risk is explained with citations to comparable
                        language. Confidence is reported honestly. When the model is
                        uncertain, the clause is flagged as such rather than guessed.
                        For consequential agreements, get a lawyer. For everything else,
                        get a second opinion in sixty seconds.
                    </p>
                    <p className="mt-normal flex flex-wrap items-center gap-x-3 gap-y-2 font-mono text-caption uppercase text-muted-foreground">
                        <span className="text-foreground">Evidence-first</span>
                        <span aria-hidden className="h-px w-4 bg-border" />
                        <span>Transparent confidence</span>
                        <span aria-hidden className="h-px w-4 bg-border" />
                        <span>Not legal advice</span>
                    </p>
                </div>
            </div>
        </section>
    );
}