import { SectionHeader } from "@/components/ui/section-header";

export function Specimen() {
  return (
    <section
      id="product"
      className="relative scroll-mt-20 px-6 py-32 pl-14 md:px-10 md:py-40 md:pl-24 lg:py-48 xl:py-56 xl:pl-28"
    >
      <div className="mx-auto max-w-[1200px]">
        <div className="mb-loose flex flex-col items-end text-right">
          <SectionHeader number="002" label="A specimen" className="mb-tight" />

          <h2 className="mb-tight font-display text-display-lg max-w-2xl font-medium text-balance">
            <span className="font-editorial">What</span> an analyzed clause looks like.
          </h2>
          <p className="text-body text-muted-foreground max-w-xl text-pretty">
            The original text on the left. Margin notes on the right, in the voice of someone who
            read it carefully so you don&apos;t have to.
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
      className="border-border bg-paper relative rounded-md border p-6 md:p-10"
      style={{ boxShadow: "0 1px 0 0 oklch(0.18 0.006 50 / 4%)" }}
    >
      <div
        aria-hidden
        className="bg-paper-rule pointer-events-none absolute top-8 bottom-8 left-0 w-px"
      />

      <p className="text-caption text-muted-foreground mb-6 flex items-center gap-2 font-mono uppercase">
        <span className="text-foreground">&sect; 8.3</span>
        <span aria-hidden className="bg-border h-px w-5" />
        <span>Indemnification</span>
      </p>

      <p className="font-editorial text-body-lg text-foreground leading-[1.7]">
        Provider shall indemnify, defend, and hold harmless Client from any and all claims, losses,
        liabilities, damages, and expenses
        <span className="bg-risk-high-soft text-risk-high px-1">
          {" "}
          arising out of or in connection with{" "}
        </span>
        this Agreement, including but not limited to attorneys&apos; fees, regardless of cause,
        including Client&apos;s own
        <span className="bg-risk-high-soft text-risk-high px-1">
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
    <aside className="gap-normal flex flex-col pt-6 md:pt-10 lg:pt-10">
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
        body="You'd be on the hook even for damages the client caused themselves. Extraordinary ask. Strike this."
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
    <div className="group border-border hover:border-foreground/60 relative border-l pl-5 transition-colors duration-200 ease-[cubic-bezier(0.23,1,0.32,1)]">
      <div className="mb-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="text-caption text-muted-foreground font-mono">Note {number}</span>
        <span className="flex items-center gap-1.5">
          <span aria-hidden className={`inline-block size-1.5 ${dotClass}`} />
          <span className={`text-caption font-mono font-medium uppercase ${labelClass}`}>
            {riskLabel}
          </span>
        </span>
      </div>
      <h3
        className="font-display text-heading-md text-foreground mb-1.5 font-medium"
        dangerouslySetInnerHTML={{ __html: title }}
      />
      <p
        className="text-body-sm text-muted-foreground"
        dangerouslySetInnerHTML={{ __html: body }}
      />
    </div>
  );
}
