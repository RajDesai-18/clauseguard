import type { ReactNode } from "react";
import { Logo } from "@/components/ui/logo";

interface AuthCardProps {
  sectionNumber: string;
  sectionLabel: string;
  heading: ReactNode;
  subtitle: string;
  children: ReactNode;
  footer?: ReactNode;
}

export function AuthCard({
  sectionNumber,
  sectionLabel,
  heading,
  subtitle,
  children,
  footer,
}: AuthCardProps) {
  return (
    <section className="flex min-h-screen flex-1 items-center justify-center px-6 py-10 md:py-12">
      <div className="w-full max-w-[580px]">
        <div className="border-border/60 bg-background border p-8 md:p-12">
          <p className="text-caption text-muted-foreground font-mono uppercase">
            <span>No. {sectionNumber}</span>
            <span className="text-border mx-2">—</span>
            <span>{sectionLabel}</span>
          </p>

          <div className="mt-8">
            <Logo size="lg" />
          </div>

          <h1 className="font-display text-foreground mt-6 text-[36px] leading-[1.05] tracking-[-0.025em]">
            {heading}
          </h1>
          <p className="text-body-lg text-muted-foreground mt-2">{subtitle}</p>

          <div className="mt-8">{children}</div>
        </div>

        {footer && (
          <p className="text-body-sm text-muted-foreground mt-4 text-center font-mono uppercase">
            {footer}
          </p>
        )}
      </div>
    </section>
  );
}
