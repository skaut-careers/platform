import type { DecisionType } from "@/lib/decisions";

export const WORKFLOW_AGENT_ID = "application_workflow";

export type WorkflowDecisionView = {
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
  signals?: { missing_signals?: string[] };
  match?: unknown;
  decision?: WorkflowDecisionView;
  output?: {
    decision: WorkflowDecisionView;
    job_signals?: { missing_signals?: string[] };
    recommended_next_steps?: string[];
  };
};

export function isDecisionType(value: unknown): value is DecisionType {
  return (
    value === "prepare" ||
    value === "queue" ||
    value === "escalate" ||
    value === "skip"
  );
}

export function workflowDecision(
  state: WorkflowAgentState,
): WorkflowDecisionView | null {
  const decision = state.output?.decision ?? state.decision;
  if (!decision || !isDecisionType(decision.decision)) return null;
  return {
    decision: decision.decision,
    score: Number(decision.score ?? 0),
    reasons: decision.reasons ?? [],
    risks: decision.risks ?? [],
    missing_information: decision.missing_information ?? [],
  };
}

export function missingSignals(state: WorkflowAgentState): string[] {
  const fromOutput = state.output?.job_signals?.missing_signals;
  if (fromOutput?.length) return fromOutput;
  const fromDecision = workflowDecision(state)?.missing_information;
  if (fromDecision?.length) return fromDecision;
  return state.signals?.missing_signals ?? [];
}

export function stageProgressLabel(state: WorkflowAgentState): string {
  if (state.signals) return "Matching profile to role and applying decision rules…";
  if (state.user_profile) return "Reading the role…";
  return "Reading your profile…";
}
