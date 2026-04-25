"use client";

import { useRouter } from "next/navigation";

export function BackButton() {
  const router = useRouter();

  return (
    <button
      type="button"
      onClick={() => router.back()}
      className="text-caption text-muted-foreground decoration-muted-foreground/40 hover:text-foreground hover:decoration-foreground/80 font-mono tracking-[0.12em] uppercase underline underline-offset-4 transition-colors duration-150 [transition-timing-function:var(--ease-out-strong)]"
    >
      Go back
    </button>
  );
}
