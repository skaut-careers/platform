import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MatchResult } from "@/components/MatchResult";
import { DECISION_COPY } from "@/lib/decisions";
import type { WorkflowDecisionView } from "@/lib/workflow";

function decision(
  overrides: Partial<WorkflowDecisionView> & Pick<WorkflowDecisionView, "decision">,
): WorkflowDecisionView {
  return {
    score: 0.8,
    reasons: [],
    risks: [],
    missing_information: [],
    ...overrides,
  };
}

describe("MatchResult", () => {
  it("renders prepare copy without a highlight list when empty", () => {
    render(
      <MatchResult decision={decision({ decision: "prepare" })} missingSignals={[]} />,
    );
    const copy = DECISION_COPY.prepare;
    expect(screen.getByText(copy.label)).toBeInTheDocument();
    expect(screen.getByText(copy.parts[0])).toBeInTheDocument();
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("prefers risks, then missing signals, then reasons, capped at 3", () => {
    render(
      <MatchResult
        decision={decision({
          decision: "queue",
          risks: ["ambiguous scope", "conflicting seniority"],
          reasons: ["matched Python", "matched FastAPI"],
        })}
        missingSignals={["salary", "visa"]}
      />,
    );
    expect(screen.getByText(DECISION_COPY.queue.label)).toBeInTheDocument();
    expect(screen.getAllByRole("listitem").map((el) => el.textContent)).toEqual([
      "ambiguous scope",
      "conflicting seniority",
      "Missing salary",
    ]);
  });

  it.each(["escalate", "skip"] as const)("renders %s label", (type) => {
    render(
      <MatchResult decision={decision({ decision: type })} missingSignals={[]} />,
    );
    expect(screen.getByText(DECISION_COPY[type].label)).toBeInTheDocument();
  });
});
