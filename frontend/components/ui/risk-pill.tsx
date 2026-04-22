import type { ReactNode } from "react";

type RiskLevel = "low" | "medium" | "high";

const STYLES: Record<RiskLevel, string> = {
  low: "bg-risk-low-soft text-risk-low",
  medium: "bg-risk-med-soft text-risk-med",
  high: "bg-risk-high-soft text-risk-high",
};

const LABELS: Record<RiskLevel, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
};

export function RiskPill({ level }: { level: RiskLevel }): ReactNode {
  return (
    <span
      className={`text-caption inline-flex items-center rounded-sm px-2 py-0.5 font-mono uppercase ${STYLES[level]}`}
    >
      {LABELS[level]}
    </span>
  );
}