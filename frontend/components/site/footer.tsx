import Link from "next/link";

/**
 * The colophon — marketing site footer.
 * Editorial sign-off + stack credits + product/colophon columns.
 *
 * Uses solid bg-background to match the nav. The bond paper texture
 * (fixed layer in RootLayout) passes through naturally. A top dossier
 * rule at the foreground/20 tone signals the end of the document.
 */
export function SiteFooter() {
    return (
        <footer className="relative border-t border-foreground/20">
            <div className="mx-auto grid w-full max-w-[1400px] grid-cols-1 gap-y-12 px-6 py-24 pl-14 md:grid-cols-12 md:gap-x-10 md:px-10 md:pl-24 lg:py-32 xl:pl-28">
                <div className="md:col-span-6 lg:col-span-5">
                    <div className="flex items-center gap-2.5">
                        <span
                            aria-hidden
                            className="inline-flex size-[18px] items-center justify-center border border-foreground"
                        >
                            <span className="size-[5px] bg-foreground" />
                        </span>
                        <span className="font-display text-[15px] font-medium tracking-tight">
                            ClauseGuard
                        </span>
                    </div>
                    <p className="mt-normal max-w-md font-editorial text-body-lg text-muted-foreground">
                        &ldquo;Most contracts are written to be survived, not understood.
                        We prefer the latter.&rdquo;
                    </p>
                    <p className="mt-normal max-w-md text-body-sm text-muted-foreground">
                        ClauseGuard is a tool, not a lawyer. Its analysis is meant to help
                        you understand contracts faster, not to replace legal advice on
                        consequential agreements.
                    </p>
                </div>

                <FooterColumn label="Product">
                    <FooterLink href="#product">How it works</FooterLink>
                    <FooterLink href="/example">Sample analysis</FooterLink>
                    <FooterLink href="/changelog">Changelog</FooterLink>
                </FooterColumn>

                <FooterColumn label="Colophon">
                    <FooterLink href="/about">About</FooterLink>
                    <FooterLink href="/docs">Documentation</FooterLink>
                    <FooterLink href="https://github.com/RajDesai-18/clauseguard">
                        GitHub
                    </FooterLink>
                    <FooterLink href="/contact">Contact</FooterLink>
                </FooterColumn>

                <FooterColumn label="Stack">
                    <FooterMeta>FastAPI &middot; Celery</FooterMeta>
                    <FooterMeta>Postgres + pgvector</FooterMeta>
                    <FooterMeta>Next.js 16 &middot; React 19</FooterMeta>
                    <FooterMeta>Tailwind 4</FooterMeta>
                </FooterColumn>
            </div>

            <div className="border-t border-border/40">
                <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-3 px-6 py-6 pl-14 md:flex-row md:items-center md:justify-between md:px-10 md:pl-24 xl:pl-28">
                    <p className="font-mono text-micro uppercase text-muted-foreground">
                        &copy; 2026 ClauseGuard &middot; Vol. 1 / Issue 4
                    </p>
                    <p className="font-mono text-micro uppercase text-muted-foreground">
                        Set in Space Grotesk, Outfit, Azeret Mono &amp; Gambetta
                    </p>
                </div>
            </div>
        </footer>
    );
}

function FooterColumn({
    label,
    children,
}: {
    label: string;
    children: React.ReactNode;
}) {
    return (
        <div className="md:col-span-2 lg:col-span-2 lg:col-start-auto">
            <p className="mb-5 font-mono text-caption uppercase text-muted-foreground">
                {label}
            </p>
            <ul className="flex flex-col gap-2.5">{children}</ul>
        </div>
    );
}

function FooterLink({
    href,
    children,
}: {
    href: string;
    children: React.ReactNode;
}) {
    return (
        <li>
            <Link
                href={href}
                className="group inline-flex items-baseline gap-1.5 text-body-sm text-foreground/85 transition-colors duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] hover:text-foreground"
            >
                <span className="border-b border-transparent pb-0.5 transition-colors duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] group-hover:border-foreground/50">
                    {children}
                </span>
            </Link>
        </li>
    );
}

function FooterMeta({ children }: { children: React.ReactNode }) {
    return (
        <li className="font-mono text-[11px] tracking-[0.06em] text-muted-foreground">
            {children}
        </li>
    );
}