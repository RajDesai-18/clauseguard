import Link from "next/link";
import type { ComponentProps } from "react";

type Variant = "primary" | "ghost";

type CTAButtonProps = {
    variant?: Variant;
    href: string;
    children: React.ReactNode;
    withArrow?: boolean;
} & Omit<ComponentProps<typeof Link>, "href" | "children">;

/**
 * Primary and secondary CTA styles used across the marketing site.
 *
 * - primary: filled ink button. Hovers with a 1% scale-up, compresses on press.
 * - ghost: text link with a persistent underline that strengthens on hover
 *   and an arrow that nudges 4px forward.
 *
 * Interaction timing follows the design system:
 * - hover transitions: 200ms with --ease-out-strong
 * - press: scale to 0.98, returns on release
 */
export function CTAButton({
    variant = "primary",
    href,
    children,
    withArrow = false,
    className = "",
    ...rest
}: CTAButtonProps) {
    if (variant === "primary") {
        return (
            <Link
                href={href}
                className={`group inline-flex items-center gap-2 rounded-[3px] bg-foreground px-5 py-3 font-display text-body font-medium tracking-[-0.005em] text-background transition-all duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] hover:bg-foreground/90 hover:scale-[1.01] active:scale-[0.98] ${className}`}
                {...rest}
            >
                <span>{children}</span>
                {withArrow && (
                    <span
                        aria-hidden
                        className="inline-block transition-transform duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] group-hover:translate-x-0.5"
                    >
                        &rarr;
                    </span>
                )}
            </Link>
        );
    }

    return (
        <Link
            href={href}
            className={`group inline-flex items-center gap-1.5 text-body text-foreground transition-colors duration-150 ${className}`}
            {...rest}
        >
            <span className="border-b border-foreground/30 pb-0.5 transition-colors duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] group-hover:border-foreground/80">
                {children}
            </span>
            {withArrow && (
                <span
                    aria-hidden
                    className="inline-block transition-transform duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] group-hover:translate-x-1"
                >
                    &rarr;
                </span>
            )}
        </Link>
    );
}