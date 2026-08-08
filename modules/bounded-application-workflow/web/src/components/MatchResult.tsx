import { DECISION_COPY, type DecisionType } from "@/lib/decisions";
import type { WorkflowDecisionView } from "@/lib/workflow";

const MAX_HIGHLIGHTS = 3;

/** Prefer risks, then a couple missing signals, then one reason — keep the panel short. */
function highlights(
  decision: WorkflowDecisionView,
  missingSignals: string[],
): string[] {
  const items: string[] = [];
  for (const risk of decision.risks) {
    if (items.length >= MAX_HIGHLIGHTS) break;
    items.push(risk);
  }
  for (const signal of missingSignals) {
    if (items.length >= MAX_HIGHLIGHTS) break;
    items.push(`Missing ${signal}`);
  }
  for (const reason of decision.reasons) {
    if (items.length >= MAX_HIGHLIGHTS) break;
    items.push(reason);
  }
  return items;
}

export function MatchResult({
  decision,
  missingSignals,
}: {
  decision: WorkflowDecisionView;
  missingSignals: string[];
}) {
  const copy = DECISION_COPY[decision.decision as DecisionType];
  const bullets = highlights(decision, missingSignals);

  return (
    <div className="flex w-full max-w-md flex-col items-center gap-4 px-1">
      <div className="flex flex-col items-center gap-2 text-center">
        <p className="font-display text-4xl font-semibold tracking-tight text-forest md:text-5xl">
          {copy.label}
        </p>
        <p className="text-sm leading-7 tracking-wide text-muted">
          {copy.parts.map((part, index) => (
            <span key={part}>
              {index > 0 ? (
                <span className="mx-2.5 text-base font-bold text-ink" aria-hidden>
                  ·
                </span>
              ) : null}
              {part}
            </span>
          ))}
        </p>
      </div>

      {bullets.length > 0 ? (
        <ul className="result-tile w-full list-disc space-y-1.5 pl-5 text-left text-sm text-ink">
          {bullets.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
