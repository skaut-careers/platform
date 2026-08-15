import { DECISION_COPY, type DecisionType } from "@/lib/decisions";
import type { WorkflowResultView } from "@/lib/workflow";

type PanelCopy = {
  title: string;
  hint: string;
  glyph: string;
  tone: string;
  field: "reasons" | "risks";
};

/** The trail metaphor: what pushes you forward, what pushes back. */
const PANELS: ReadonlyArray<PanelCopy> = [
  {
    title: "Tailwinds",
    hint: "carrying you forward",
    glyph: "↑",
    tone: "is-tailwind",
    field: "reasons",
  },
  {
    title: "Headwinds",
    hint: "slowing you down",
    glyph: "↓",
    tone: "is-headwind",
    field: "risks",
  },
];

function Panel({ copy, items }: { copy: PanelCopy; items: string[] }) {
  return (
    <section className={`result-panel ${copy.tone} w-full text-left`}>
      <h3 className="result-panel-title mb-1.5">
        <span className="result-panel-glyph" aria-hidden>
          {copy.glyph}
        </span>
        {copy.title}
        <span className="result-panel-hint">· {copy.hint}</span>
      </h3>
      <ul className="list-disc space-y-1.5 pl-5 text-sm text-ink">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

export function MatchResult({ result }: { result: WorkflowResultView }) {
  const copy = DECISION_COPY[result.decision as DecisionType];
  const panels = PANELS.map((copy) => ({
    copy,
    items: result[copy.field],
  })).filter((panel) => panel.items.length > 0);

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

      {panels.length > 0 ? (
        <div className="flex w-full flex-col gap-3">
          {panels.map((panel) => (
            <Panel key={panel.copy.field} copy={panel.copy} items={panel.items} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
