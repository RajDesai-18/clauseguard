import { SectionHeader } from "@/components/ui/section-header";

export function Specimen() {
    return (
        <section
            id="product"
            className="relative scroll-mt-20 px-6 py-32 pl-14 md:px-10 md:py-40 md:pl-24 lg:py-48 xl:py-56 xl:pl-28"
        >
            <div className="mx-auto max-w-[1200px]">
                <div className="mb-loose flex flex-col items-end text-right">
                    <SectionHeader
                        number="002"
                        label="A specimen"
                        className="mb-tight"
                    />

                    <h2 className="mb-tight max-w-2xl text-balance font-display font-medium text-display-lg">
                        <span className="font-editorial">What</span> an analyzed clause
                        looks like.
                    </h2>
                    <p className="max-w-xl text-pretty text-body text-muted-foreground">
                        The original text on the left. Margin notes on the right, in the
                        voice of someone who read it carefully so you don&apos;t have to.
                    </p>
                </div>

                <div className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)] lg:gap-14">
                    <ClauseCard />
                    <Annotations />
                </div>
            </div>
        </section>
    );
}

function ClauseCard() {
    return (
        <article
            className="relative rounded-md border border-border bg-paper p-6 md:p-10"
            style={{ boxShadow: "0 1px 0 0 oklch(0.18 0.006 50 / 4%)" }}
        >
            <div
                aria-hidden
                className="pointer-events-none absolute left-0 top-8 bottom-8 w-px bg-paper-rule"
            />

            <p className="mb-6 flex items-center gap-2 font-mono text-caption uppercase text-muted-foreground">
                <span className="text-foreground">&sect; 8.3</span>
                <span aria-hidden className="h-px w-5 bg-border" />
                <span>Indemnification</span>
            </p>

            <p className="font-editorial text-body-lg leading-[1.7] text-foreground">
                Provider shall indemnify, defend, and hold harmless Client from any
                and all claims, losses, liabilities, damages, and expenses
                <span className="bg-risk-high-soft px-1 text-risk-high">
                    {" "}
                    arising out of or in connection with{" "}
                </span>
                this Agreement, including but not limited to attorneys&apos; fees,
                regardless of cause, including Client&apos;s own
                <span className="bg-risk-high-soft px-1 text-risk-high">
                    {" "}
                    negligence or willful misconduct
                </span>
                .
            </p>
        </article>
    );
}

function Annotations() {
    return (
        <aside className="flex flex-col gap-normal pt-6 md:pt-10 lg:pt-10">
            <Annotation
                risk="high"
                number="1"
                title="Unlimited indemnity"
                body="Clause covers &lsquo;any and all&rsquo; claims with no cap on liability. Market standard for your role is a cap at 1&times; annual fees."
            />
            <Annotation
                risk="high"
                number="2"
                title="Client&rsquo;s own misconduct"
                body="You&apos;d be on the hook even for damages the client caused themselves. Extraordinary ask. Strike this."
            />
            <Annotation
                risk="med"
                number="3"
                title="Attorneys&rsquo; fees included"
                body="Not unusual, but combined with the items above, the exposure is meaningful."
            />
        </aside>
    );
}

type Risk = "low" | "med" | "high";

function Annotation({
    risk,
    number,
    title,
    body,
}: {
    risk: Risk;
    number: string;
    title: string;
    body: string;
}) {
    const dotClass = {
        low: "bg-risk-low",
        med: "bg-risk-med",
        high: "bg-risk-high",
    }[risk];

    const labelClass = {
        low: "text-risk-low",
        med: "text-risk-med",
        high: "text-risk-high",
    }[risk];

    const riskLabel = {
        low: "Low risk",
        med: "Medium risk",
        high: "High risk",
    }[risk];

    return (
        <div className="group relative border-l border-border pl-5 transition-colors duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] hover:border-foreground/60">
            <div className="mb-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <span className="font-mono text-caption text-muted-foreground">
                    Note {number}
                </span>
                <span className="flex items-center gap-1.5">
                    <span aria-hidden className={`inline-block size-1.5 ${dotClass}`} />
                    <span
                        className={`font-mono text-caption uppercase font-medium ${labelClass}`}
                    >
                        {riskLabel}
                    </span>
                </span>
            </div>
            <h3
                className="mb-1.5 font-display text-heading-md font-medium text-foreground"
                dangerouslySetInnerHTML={{ __html: title }}
            />
            <p
                className="text-body-sm text-muted-foreground"
                dangerouslySetInnerHTML={{ __html: body }}
            />
        </div>
    );
}