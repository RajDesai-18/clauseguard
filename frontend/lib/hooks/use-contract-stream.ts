"use client";

import { useEffect, useRef, useState } from "react";

export type StreamStatus =
  | "connecting"
  | "queued"
  | "parsing"
  | "analyzing"
  | "scoring"
  | "redlining"
  | "complete"
  | "failed"
  | "error";

export interface ProgressEvent {
  contract_id: string;
  status: string;
  detail: string;
  current_step: number;
  total_steps: number;
}

export interface StreamState {
  status: StreamStatus;
  detail: string;
  currentStep: number;
  totalSteps: number;
  error: string | null;
  events: ProgressEvent[];
}

const TERMINAL_STATUSES: StreamStatus[] = ["complete", "failed", "error"];

export function useContractStream(contractId: string | null): StreamState {
  const [state, setState] = useState<StreamState>({
    status: "connecting",
    detail: "",
    currentStep: 0,
    totalSteps: 5,
    error: null,
    events: [],
  });

  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!contractId) return;

    const url = `/api/contracts/${contractId}/stream`;
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.addEventListener("connected", () => {
      setState((prev) => ({ ...prev, status: "connecting", error: null }));
    });

    eventSource.addEventListener("error", (event) => {
      const errEvent = event as MessageEvent;
      let message = "Connection lost";
      if (errEvent.data) {
        try {
          const parsed = JSON.parse(errEvent.data);
          message = parsed.message ?? message;
        } catch {
          // ignore parse error
        }
      }
      setState((prev) => ({
        ...prev,
        status: "error",
        error: message,
      }));
    });

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as ProgressEvent;
        setState((prev) => {
          const nextStatus = normalizeStatus(data.status);
          const nextState: StreamState = {
            status: nextStatus,
            detail: data.detail,
            currentStep: data.current_step,
            totalSteps: data.total_steps,
            error: null,
            events: [...prev.events, data],
          };

          if (TERMINAL_STATUSES.includes(nextStatus)) {
            eventSource.close();
          }

          return nextState;
        });
      } catch (err) {
        console.error("Failed to parse SSE event:", err);
      }
    };

    eventSource.onerror = () => {
      // Native EventSource error (network drop, server close, etc.)
      // Browser auto-reconnects unless we close. We let it try.
      setState((prev) => {
        if (TERMINAL_STATUSES.includes(prev.status)) return prev;
        return { ...prev, status: "error", error: "Connection interrupted" };
      });
    };

    return () => {
      eventSource.close();
      eventSourceRef.current = null;
    };
  }, [contractId]);

  return state;
}

function normalizeStatus(status: string): StreamStatus {
  const known: StreamStatus[] = [
    "queued",
    "parsing",
    "analyzing",
    "scoring",
    "redlining",
    "complete",
    "failed",
  ];
  if (known.includes(status as StreamStatus)) {
    return status as StreamStatus;
  }
  return "connecting";
}
