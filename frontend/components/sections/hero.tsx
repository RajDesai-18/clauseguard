import { CTAButton } from "@/components/ui/cta-button";
import { SectionHeader } from "@/components/ui/section-header";

export function Hero() {
    return (
        <section
            id="hero"
            className="relative px-6 py-32 pl-14 md:px-10 md:py-40 md:pl-24 lg:py-48 xl:py-56 xl:pl-28"
        >
            <div className="max-w-3xl">
                <SectionHeader
                    number="001"
                    label="A contract review field guide"
                    className="mb-tight"
                />

                <h1 className="mb-normal text-balance font-display font-medium text-display-xl">
                    Read the{" "}
                    <span className="font-editorial text-foreground">fine print</span>
                    <br />
                    <span className="text-muted-foreground">before you</span> sign it.
                </h1>

                <p className="max-w-xl text-pretty text-body-lg text-muted-foreground">
                    Upload any NDA, MSA, or SOW. ClauseGuard returns a plain-English risk
                    breakdown, clause by clause, with AI-suggested redlines. Built for
                    the 99% of people who don&apos;t have a lawyer on retainer.
                </p>

                <div className="mt-normal flex flex-wrap items-center gap-5">
                    <CTAButton variant="primary" href="/upload" withArrow>
                        Analyze a contract
                    </CTAButton>
                    <CTAButton variant="ghost" href="/example" withArrow>
                        or see an example
                    </CTAButton>
                </div>
            </div>
        </section>
    );
}