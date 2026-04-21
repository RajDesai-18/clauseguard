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
      className="border-border/50 relative scroll-mt-20 border-t px-6 py-32 pl-14 md:px-10 md:py-40 md:pl-24 lg:py-48 xl:py-56 xl:pl-28"
    >
      <div className="mx-auto max-w-[1200px]">
        <SectionHeader number="003" label="The procedure" className="mb-tight" />

        <h2 className="mb-loose font-display text-display-lg max-w-3xl font-medium text-balance">
          Four stages, <span className="font-editorial">about a minute</span>, from upload to
          redline.
        </h2>

        <ol className="grid grid-cols-1 gap-y-12 sm:grid-cols-2 sm:gap-x-8 lg:grid-cols-4 lg:gap-x-10">
          {steps.map((step) => (
            <li key={step.no} className="group relative">
              <div className="mb-5 flex items-center gap-4">
                <span className="text-caption text-muted-foreground group-hover:text-foreground font-mono uppercase transition-colors duration-200">
                  Step {step.no}
                </span>
                <span
                  aria-hidden
                  className="bg-border group-hover:bg-foreground h-px flex-1 transition-[background-color,height] duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] group-hover:h-[2px]"
                />
              </div>

              <h3 className="mb-tight font-display text-heading-lg text-foreground font-medium">
                {step.title}
                <span aria-hidden className="text-muted-foreground/40 ml-1">
                  .
                </span>
              </h3>

              <p className="text-body-sm text-muted-foreground">{step.body}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
