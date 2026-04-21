import { SectionHeader } from "@/components/ui/section-header";

const steps = [
    {
        no: "i",
        title: "Upload",
        body: "Drag a PDF or DOCX. NDAs, MSAs, SOWs, leases. Up to 10MB. No account required for your first analysis.",
    },
    {
        no: "ii",
        title: "Parse",
        body: "Structure is preserved. Clauses are extracted by type — indemnity, termination, IP, confidentiality, auto-renewal.",
    },
    {
        no: "iii",
        title: "Analyze",
        body: "Each clause is compared to market-standard language. Risk is assigned, confidence is reported, and the reasoning is shown.",
    },
    {
        no: "iv",
        title: "Redline",
        body: "For risky clauses, you get a suggested revision in plain English and a side-by-side diff you can export to DOCX.",
    },
];

export function Process() {
    return (
        <section
            id="process"
            className="relative scroll-mt-20 border-t border-border/50 px-6 py-32 pl-14 md:px-10 md:py-40 md:pl-24 lg:py-48 xl:py-56 xl:pl-28"
        >
            <div className="mx-auto max-w-[1200px]">
                <SectionHeader number="003" label="The procedure" className="mb-tight" />

                <h2 className="mb-loose max-w-3xl text-balance font-display font-medium text-display-lg">
                    Four stages, <span className="font-editorial">about a minute</span>,
                    from upload to redline.
                </h2>

                <ol className="grid grid-cols-1 gap-y-12 sm:grid-cols-2 sm:gap-x-8 lg:grid-cols-4 lg:gap-x-10">
                    {steps.map((step) => (
                        <li key={step.no} className="group relative">
                            <div className="mb-5 flex items-center gap-4">
                                <span className="font-mono text-caption uppercase text-muted-foreground transition-colors duration-200 group-hover:text-foreground">
                                    Step {step.no}
                                </span>
                                <span
                                    aria-hidden
                                    className="h-px flex-1 bg-border transition-[background-color,height] duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] group-hover:h-[2px] group-hover:bg-foreground"
                                />
                            </div>

                            <h3 className="mb-tight font-display text-heading-lg font-medium text-foreground">
                                {step.title}
                                <span aria-hidden className="ml-1 text-muted-foreground/40">
                                    .
                                </span>
                            </h3>

                            <p className="text-body-sm text-muted-foreground">
                                {step.body}
                            </p>
                        </li>
                    ))}
                </ol>
            </div>
        </section>
    );
}