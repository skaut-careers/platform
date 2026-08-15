import type { DecisionType } from "@/lib/decisions";

export const WORKFLOW_AGENT_ID = "application_workflow";

/** Client-facing result — mirrors backend ``WorkflowOutput``. */
export type WorkflowResultView = {
  decision: DecisionType;
  score: number;
  reasons: string[];
  risks: string[];
  missing_information: string[];
};

export type WorkflowAgentState = {
  profile_text?: string;
  job_description_text?: string;
  user_profile?: unknown;
  job_signals?: unknown;
  match_decision?: WorkflowResultView & Record<string, unknown>;
  output?: WorkflowResultView;
};

export function isDecisionType(value: unknown): value is DecisionType {
  return (
    value === "strong" ||
    value === "prepare" ||
    value === "queue" ||
    value === "skip"
  );
}

export function workflowResult(
  state: WorkflowAgentState,
): WorkflowResultView | null {
  const result = state.output ?? state.match_decision;
  if (!result || !isDecisionType(result.decision)) return null;
  return {
    decision: result.decision,
    score: Number(result.score ?? 0),
    reasons: result.reasons ?? [],
    risks: result.risks ?? [],
    missing_information: result.missing_information ?? [],
  };
}

export function stageProgressLabel(state: WorkflowAgentState): string {
  if (state.job_signals) return "Matching profile to role and applying decision rules…";
  if (state.user_profile) return "Reading the role…";
  return "Reading your profile…";
}
