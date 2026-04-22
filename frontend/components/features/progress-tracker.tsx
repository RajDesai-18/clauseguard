"use client";

import { useEffect } from "react";
import { Check, X } from "lucide-react";
import { useContractStream } from "@/lib/hooks/use-contract-stream";
import type { StreamStatus } from "@/lib/hooks/use-contract-stream";

interface Step {
  key: StreamStatus;
  label: string;
  caption: string;
}

const STEPS: Step[] = [
  { key: "queued", label: "Queued", caption: "001" },
  { key: "parsing", label: "Parse", caption: "002" },
  { key: "analyzing", label: "Analyze", caption: "003" },
  { key: "scoring", label: "Score", caption: "004" },
  { key: "redlining", label: "Redline", caption: "005" },
];

const STEP_ORDER: StreamStatus[] = [
  "queued",
  "parsing",
  "analyzing",
  "scoring",
  "redlining",
  "complete",
];

interface Props {
  contractId: string;
  onStatusChange?: (status: StreamStatus) => void;
}

export function ProgressTracker({ contractId, onStatusChange }: Props) {
  const stream = useContractStream(contractId);

  useEffect(() => {
    if (onStatusChange) onStatusChange(stream.status);
  }, [stream.status, onStatusChange]);

  const currentIndex = STEP_ORDER.indexOf(stream.status);
  const isFailed = stream.status === "failed";
  const isComplete = stream.status === "complete";
  const isError = stream.status === "error";

  return (
    <div className="space-y-8">
      <div className="flex items-baseline justify-between">
        <p className="text-caption text-muted-foreground font-mono uppercase">Pipeline status</p>
        <p className="text-caption text-muted-foreground font-mono">
          {Math.max(stream.currentStep, 0)} / {stream.totalSteps}
        </p>
      </div>

      <ol className="border-border/40 grid grid-cols-5 gap-0 border-y">
        {STEPS.map((step, index) => {
          const stepState = getStepState({
            stepIndex: index,
            currentIndex,
            isFailed,
            isComplete,
          });
          return (
            <StepCell
              key={step.key}
              step={step}
              state={stepState}
              isLast={index === STEPS.length - 1}
            />
          );
        })}
      </ol>

      <StatusDetail
        status={stream.status}
        detail={stream.detail}
        error={stream.error}
        isError={isError}
        isFailed={isFailed}
        isComplete={isComplete}
      />
    </div>
  );
}

type StepState = "pending" | "active" | "complete" | "failed";

function getStepState({
  stepIndex,
  currentIndex,
  isFailed,
  isComplete,
}: {
  stepIndex: number;
  currentIndex: number;
  isFailed: boolean;
  isComplete: boolean;
}): StepState {
  if (isComplete) return "complete";
  if (isFailed && stepIndex === currentIndex) return "failed";
  if (isFailed && stepIndex < currentIndex) return "complete";
  if (stepIndex < currentIndex) return "complete";
  if (stepIndex === currentIndex) return "active";
  return "pending";
}

function StepCell({ step, state, isLast }: { step: Step; state: StepState; isLast: boolean }) {
  return (
    <li className={`relative px-4 py-5 ${isLast ? "" : "border-border/40 border-r"}`}>
      {state === "active" && (
        <span aria-hidden className="bg-foreground absolute inset-x-0 top-0 h-px" />
      )}
      <div className="flex items-center gap-2">
        <StepMarker state={state} />
        <p className="text-caption text-muted-foreground font-mono uppercase">{step.caption}</p>
      </div>
      <p
        className={`font-display mt-2 text-[15px] font-medium tracking-[-0.01em] ${
          state === "pending"
            ? "text-muted-foreground/60"
            : state === "failed"
              ? "text-destructive"
              : "text-foreground"
        }`}
      >
        {step.label}
      </p>
    </li>
  );
}

function StepMarker({ state }: { state: StepState }) {
  if (state === "complete") {
    return (
      <span
        aria-hidden
        className="border-foreground bg-foreground text-background flex size-4 items-center justify-center rounded-full border"
      >
        <Check className="size-2.5" strokeWidth={2.5} />
      </span>
    );
  }
  if (state === "failed") {
    return (
      <span
        aria-hidden
        className="border-destructive bg-destructive text-background flex size-4 items-center justify-center rounded-full border"
      >
        <X className="size-2.5" strokeWidth={2.5} />
      </span>
    );
  }
  if (state === "active") {
    return (
      <span aria-hidden className="relative flex size-4 items-center justify-center">
        <span className="bg-foreground/30 absolute inset-0 animate-ping rounded-full" />
        <span className="bg-foreground relative size-2 rounded-full" />
      </span>
    );
  }
  return (
    <span
      aria-hidden
      className="border-border bg-background flex size-4 items-center justify-center rounded-full border"
    />
  );
}

function StatusDetail({
  status,
  detail,
  error,
  isError,
  isFailed,
  isComplete,
}: {
  status: StreamStatus;
  detail: string;
  error: string | null;
  isError: boolean;
  isFailed: boolean;
  isComplete: boolean;
}) {
  if (isError) {
    return (
      <div className="border-destructive/40 bg-destructive/5 rounded-sm border px-4 py-3">
        <p className="text-caption text-destructive mb-1 font-mono uppercase">Stream error</p>
        <p className="text-body-sm text-foreground">
          {error ?? "Lost connection to the analysis stream."}
        </p>
      </div>
    );
  }

  if (isFailed) {
    return (
      <div className="border-destructive/40 bg-destructive/5 rounded-sm border px-4 py-3">
        <p className="text-caption text-destructive mb-1 font-mono uppercase">Pipeline failed</p>
        <p className="text-body-sm text-foreground">
          {detail || "Analysis didn't complete. The contract is preserved if you'd like to retry."}
        </p>
      </div>
    );
  }

  if (isComplete) {
    return (
      <p className="text-body-sm text-muted-foreground">
        Analysis complete. Loading results&hellip;
      </p>
    );
  }

  if (status === "connecting") {
    return (
      <p className="text-body-sm text-muted-foreground">
        Connecting to the analysis stream&hellip;
      </p>
    );
  }

  return <p className="text-body-sm text-muted-foreground">{detail || "Working&hellip;"}</p>;
}
