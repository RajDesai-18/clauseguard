"use client";

import { useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import type { ClauseDetail } from "@/lib/api/api-client";

interface Props {
  clause: ClauseDetail;
}

/**
 * Annotated Brief design (v4 — editorial). Headings sit flush-left as
 * section anchors; the original contract text and verdict strip are
 * indented into a reading "passage" constrained to ~75ch. Reads like
 * a legal brief: title in the margin, text quoted in. The right
 * margin is intentional editorial whitespace, not a bug.
 */
export function ClauseCard({ clause }: Props) {
  const [open, setOpen] = useState(false);

  const positionLabel = String(clause.position).padStart(3, "0");
  const typeLabel = formatClauseType(clause.clause_type);
  const isRisky = clause.risk_level === "yellow" || clause.risk_level === "red";
  const isPending = clause.risk_level === null;
  const stripStyle = isRisky ? STRIP_STYLES[clause.risk_level as "yellow" | "red"] : null;
  const originalText = normalizeContractText(clause.original_text);
  const headline = clause.explanation ? firstSentence(clause.explanation) : "";
  const restOfExplanation = clause.explanation ? restAfterFirstSentence(clause.explanation) : "";

  return (
    <article className="space-y-4">
      <header className="space-y-1.5">
        <div className="flex items-baseline justify-normal gap-3">
          <p className="text-caption text-muted-foreground font-mono tracking-[0.08em] uppercase">
            Clause {positionLabel}
          </p>
          {isPending && (
            <p className="text-body-sm text-muted-foreground/70 font-mono tracking-[0.08em] uppercase">
              Pending
            </p>
          )}
        </div>
        <h3 className="text-foreground font-display text-[22px] leading-[1.2] font-medium tracking-[-0.01em]">
          {typeLabel}
        </h3>
      </header>

      <p className="text-muted-foreground text-[15px] leading-[1.75]">{originalText}</p>

      {isRisky && stripStyle && headline && (
        <div className="max-w-[95ch] pt-1">
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-expanded={open}
            className={`bg-card hover:bg-card/70 focus-visible:bg-card/80 block w-full border-l-2 ${stripStyle.border} rounded-r-sm py-3.5 pr-4 pl-4 text-left transition-colors duration-150 focus-visible:outline-none`}
          >
            <div className="flex items-start gap-3">
              <div className="min-w-0 flex-1 space-y-1.5">
                <p
                  className={`text-caption font-mono tracking-[0.08em] uppercase ${stripStyle.label}`}
                >
                  {stripStyle.text}
                </p>
                <p className="text-foreground text-[15px] leading-[1.5] font-medium">{headline}</p>
              </div>
              <ChevronDown
                className={`text-muted-foreground ease-out-strong mt-1 size-4 shrink-0 transition-transform duration-200 ${
                  open ? "rotate-180" : ""
                }`}
                strokeWidth={1.5}
                aria-hidden
              />
            </div>
          </button>

          <div
            className="ease-out-strong grid transition-[grid-template-rows] duration-200"
            style={{ gridTemplateRows: open ? "1fr" : "0fr" }}
            aria-hidden={!open}
          >
            <div className="overflow-hidden">
              <div className="border-border/40 mt-5 ml-4 space-y-7 border-l pt-1 pl-5">
                {restOfExplanation && (
                  <p className="text-foreground text-[16px] leading-[1.75]">{restOfExplanation}</p>
                )}

                {clause.market_comparison && (
                  <Section label="Market comparison">
                    <p className="text-foreground text-[16px] leading-[1.75]">
                      {clause.market_comparison}
                    </p>
                  </Section>
                )}

                {clause.suggested_redline && (
                  <Section label="Suggested revision">
                    <RevisionBlock original={originalText} revised={clause.suggested_redline} />
                  </Section>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </article>
  );
}

function Section({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="space-y-2.5">
      <p className="text-caption text-muted-foreground font-mono tracking-[0.08em] uppercase">
        {label}
      </p>
      {children}
    </div>
  );
}

function RevisionBlock({ original, revised }: { original: string; revised: string }) {
  const [showOriginal, setShowOriginal] = useState(false);
  const revisedNormalized = normalizeContractText(revised);
  return (
    <div className="space-y-3">
      <div className="border-border/40 bg-card rounded-sm border p-4">
        <p className="text-foreground text-[15px] leading-[1.75]">{revisedNormalized}</p>
      </div>
      <button
        type="button"
        onClick={() => setShowOriginal((s) => !s)}
        aria-expanded={showOriginal}
        className="border-border bg-card hover:bg-foreground/4 hover:border-border/80 focus-visible:bg-foreground/4 text-foreground/90 hover:text-foreground inline-flex items-center gap-2 rounded-sm border px-3 py-2 font-mono text-[11px] tracking-[0.08em] uppercase transition-colors duration-150 focus-visible:outline-none"
      >
        Compare to original
        <ChevronDown
          className={`ease-out-strong size-3.5 transition-transform duration-200 ${
            showOriginal ? "rotate-180" : ""
          }`}
          strokeWidth={1.5}
          aria-hidden
        />
      </button>
      {showOriginal && (
        <div className="border-border/40 mt-2 border-t border-dashed pt-4">
          <p className="text-caption text-muted-foreground mb-2 font-mono tracking-[0.08em] uppercase">
            Original
          </p>
          <p className="text-foreground/85 text-[15px] leading-[1.7]">{original}</p>
        </div>
      )}
    </div>
  );
}

const STRIP_STYLES = {
  yellow: {
    border: "border-l-risk-med",
    label: "text-risk-med",
    text: "Watch",
  },
  red: {
    border: "border-l-risk-high",
    label: "text-risk-high",
    text: "High risk",
  },
} as const;

function formatClauseType(snake: string): string {
  return snake
    .split("_")
    .map((w) => (w.length === 0 ? w : w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()))
    .join(" ");
}

/**
 * PDF parsers preserve column-based line breaks. Single newlines
 * within a paragraph become spaces; double newlines (paragraph
 * breaks) are preserved. Collapses indentation runs that the parser
 * leaves behind.
 */
function normalizeContractText(text: string): string {
  return text
    .trim()
    .replace(/(?<!\n)\n(?!\n)/g, " ")
    .replace(/[ \t]+/g, " ")
    .trim();
}

function firstSentence(text: string, maxLength = 220): string {
  const trimmed = text.trim().replace(/\s+/g, " ");
  const match = trimmed.match(/^[^.!?]+[.!?]/);
  const sentence = match ? match[0].trim() : trimmed;
  if (sentence.length > maxLength) {
    return sentence.slice(0, maxLength).trimEnd() + "\u2026";
  }
  return sentence;
}

function restAfterFirstSentence(text: string): string {
  const trimmed = text.trim();
  const match = trimmed.match(/^[^.!?]+[.!?]\s*/);
  if (!match) return "";
  return trimmed.slice(match[0].length).trim();
}
