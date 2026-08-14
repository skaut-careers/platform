import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MatchResult } from "@/components/MatchResult";
import { DECISION_COPY } from "@/lib/decisions";
import type { WorkflowResultView } from "@/lib/workflow";

function result(
  overrides: Partial<WorkflowResultView> & Pick<WorkflowResultView, "decision">,
): WorkflowResultView {
  return {
    score: 0.8,
    reasons: [],
    risks: [],
    missing_information: [],
    ...overrides,
  };
}

describe("MatchResult", () => {
  it("renders strong copy without panels when every list is empty", () => {
    render(<MatchResult result={result({ decision: "strong" })} />);
    const copy = DECISION_COPY.strong;
    expect(screen.getByText(copy.label)).toBeInTheDocument();
    expect(screen.getByText(copy.parts[0])).toBeInTheDocument();
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("renders tailwinds, headwinds, and fog panels capped at 3 items each", () => {
    render(
      <MatchResult
        result={result({
          decision: "queue",
          reasons: ["matched Python", "matched FastAPI", "matched SQL", "matched Docker"],
          risks: ["ambiguous scope", "conflicting seniority"],
          missing_information: ["Job posting missing signal: salary"],
        })}
      />,
    );
    expect(screen.getByText(DECISION_COPY.queue.label)).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 3 }).map((el) => el.textContent)).toEqual([
      expect.stringContaining("Tailwinds"),
      expect.stringContaining("Headwinds"),
      expect.stringContaining("Fog"),
    ]);
    expect(screen.getAllByRole("list")).toHaveLength(3);
    expect(screen.getAllByRole("listitem").map((el) => el.textContent)).toEqual([
      "matched Python",
      "matched FastAPI",
      "matched SQL",
      "ambiguous scope",
      "conflicting seniority",
      "Job posting missing signal: salary",
    ]);
  });

  it("omits panels whose list is empty", () => {
    render(
      <MatchResult result={result({ decision: "skip", risks: ["severe seniority mismatch"] })} />,
    );
    expect(screen.getAllByRole("heading", { level: 3 }).map((el) => el.textContent)).toEqual([
      expect.stringContaining("Headwinds"),
    ]);
  });
});
