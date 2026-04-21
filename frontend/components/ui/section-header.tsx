export function SectionHeader({
    number,
    label,
    className = "",
}: {
    number: string;
    label: string;
    className?: string;
}) {
    return (
        <p
            className={`flex items-center gap-3 font-mono text-caption uppercase text-muted-foreground ${className}`}
        >
            <span className="font-medium text-foreground">No. {number}</span>
            <span aria-hidden className="h-px w-7 bg-border" />
            <span>{label}</span>
        </p>
    );
}