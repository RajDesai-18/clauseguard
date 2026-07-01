import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { SearchView } from "@/components/features/search-view";
import type { SearchResponse } from "@/lib/api/api-client";
import { ApiError, UnauthorizedError } from "@/lib/api/api-client";

// Mock only the network call; keep the real error classes so the
// component's `instanceof` checks behave exactly as in production.
vi.mock("@/lib/api/api-client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/api-client")>();
  return {
    ...actual,
    searchClausesClient: vi.fn(),
  };
});

// Pull the mocked reference after the mock is registered.
const { searchClausesClient } = await import("@/lib/api/api-client");
const mockSearch = vi.mocked(searchClausesClient);

const SAMPLE: SearchResponse = {
  query: "termination",
  total_hits: 1,
  groups: [
    {
      contract_id: "c1",
      file_name: "Northwind-MSA.docx",
      contract_type: "msa",
      overall_risk: "high",
      top_similarity: 0.53,
      hits: [
        {
          clause_id: "h1",
          clause_type: "limitation_of_liability",
          risk_level: "yellow",
          original_text: "Each party's total liability will not exceed fees paid.",
          explanation: "The cap is unusually low. It limits your recovery.",
          position: 15,
          similarity: 0.53,
        },
      ],
    },
  ],
};

const EMPTY: SearchResponse = { query: "zzz", total_hits: 0, groups: [] };

beforeEach(() => {
  mockSearch.mockReset();
});

describe("SearchView", () => {
  it("shows the example prompts before any search", () => {
    render(<SearchView />);
    expect(screen.getByText(/try/i)).toBeInTheDocument();
    // An example chip is present and clickable.
    expect(screen.getByRole("button", { name: /unlimited liability/i })).toBeInTheDocument();
    // No results section yet.
    expect(screen.queryByText(/match(es)? across/i)).not.toBeInTheDocument();
  });

  it("renders grouped results after a successful search", async () => {
    mockSearch.mockResolvedValueOnce(SAMPLE);
    const user = userEvent.setup();
    render(<SearchView />);

    await user.type(screen.getByLabelText(/search contracts/i), "termination");
    await user.click(screen.getByRole("button", { name: /^search$/i }));

    await waitFor(() => {
      expect(screen.getByText("Northwind-MSA.docx")).toBeInTheDocument();
    });
    // The hit's clause label and explanation headline render.
    expect(screen.getByText(/limitation of liability/i)).toBeInTheDocument();
    expect(screen.getByText(/the cap is unusually low/i)).toBeInTheDocument();
    // The result summary line.
    expect(screen.getByText(/1 match across 1 contract/i)).toBeInTheDocument();
  });

  it("shows the empty state when a search returns no matches", async () => {
    mockSearch.mockResolvedValueOnce(EMPTY);
    const user = userEvent.setup();
    render(<SearchView />);

    await user.type(screen.getByLabelText(/search contracts/i), "zzz");
    await user.click(screen.getByRole("button", { name: /^search$/i }));

    await waitFor(() => {
      expect(screen.getByText(/no matches/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/nothing turned up/i)).toBeInTheDocument();
  });

  it("surfaces the backend message on ApiError", async () => {
    mockSearch.mockRejectedValueOnce(
      new ApiError("Search is temporarily unavailable.", 503, "SEARCH_UNAVAILABLE", "req-123")
    );
    const user = userEvent.setup();
    render(<SearchView />);

    await user.type(screen.getByLabelText(/search contracts/i), "termination");
    await user.click(screen.getByRole("button", { name: /^search$/i }));

    await waitFor(() => {
      expect(screen.getByText(/temporarily unavailable/i)).toBeInTheDocument();
    });
  });

  it("shows a session-expired message on UnauthorizedError", async () => {
    mockSearch.mockRejectedValueOnce(new UnauthorizedError());
    const user = userEvent.setup();
    render(<SearchView />);

    await user.type(screen.getByLabelText(/search contracts/i), "termination");
    await user.click(screen.getByRole("button", { name: /^search$/i }));

    await waitFor(() => {
      expect(screen.getByText(/session has expired/i)).toBeInTheDocument();
    });
  });

  it("does not search when the query is under two characters", async () => {
    const user = userEvent.setup();
    render(<SearchView />);

    await user.type(screen.getByLabelText(/search contracts/i), "a");
    // Button should be disabled, so a click does nothing.
    const button = screen.getByRole("button", { name: /^search$/i });
    expect(button).toBeDisabled();
    expect(mockSearch).not.toHaveBeenCalled();
  });
});
