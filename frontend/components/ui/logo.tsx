import Link from "next/link";

type LogoSize = "md" | "lg";
type MarkSize = "sm" | "md" | "lg";

interface LogoProps {
  asLink?: boolean;
  size?: LogoSize;
  className?: string;
}

interface LogoMarkProps {
  size?: MarkSize;
  className?: string;
}

const sizeMap = {
  md: {
    square: "size-[18px]",
    dot: "size-[5px]",
    wordmark: "text-[15px]",
    gap: "gap-2.5",
  },
  lg: {
    square: "size-[22px]",
    dot: "size-[6px]",
    wordmark: "text-[20px]",
    gap: "gap-2.5",
  },
} as const;

const markSizeMap = {
  sm: { square: "size-[16px]", dot: "size-[4px]" },
  md: { square: "size-[18px]", dot: "size-[5px]" },
  lg: { square: "size-[22px]", dot: "size-[6px]" },
} as const;

/**
 * Logo mark only (the bordered square with a dot). No wordmark.
 * Used where the full Logo is too wide, e.g. the 72px navigation rail.
 * Preserves the same hover treatment as Logo when wrapped in a `group`.
 */
export function LogoMark({ size = "md", className }: LogoMarkProps) {
  const s = markSizeMap[size];
  return (
    <span
      aria-hidden
      className={`border-foreground group-hover:bg-foreground inline-flex ${s.square} items-center justify-center border transition-colors duration-200 ease-[cubic-bezier(0.23,1,0.32,1)] ${className ?? ""}`}
    >
      <span
        className={`bg-foreground group-hover:bg-background ${s.dot} transition-colors duration-200 ease-[cubic-bezier(0.23,1,0.32,1)]`}
      />
    </span>
  );
}

export function Logo({ asLink = true, size = "md", className }: LogoProps) {
  const s = sizeMap[size];

  const inner = (
    <span className={`group inline-flex items-center ${s.gap} ${className ?? ""}`}>
      <LogoMark size={size === "lg" ? "lg" : "md"} />
      <span className={`font-display ${s.wordmark} font-medium tracking-tight`}>ClauseGuard</span>
    </span>
  );

  if (!asLink) return inner;

  return (
    <Link href="/" aria-label="ClauseGuard home">
      {inner}
    </Link>
  );
}