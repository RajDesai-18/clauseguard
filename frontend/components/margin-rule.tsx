export function MarginRule({ offsetClass = "left-16" }: { offsetClass?: string }) {
  return (
    <div
      aria-hidden
      className={`bg-paper-rule pointer-events-none absolute top-0 bottom-0 w-px ${offsetClass}`}
    />
  );
}
