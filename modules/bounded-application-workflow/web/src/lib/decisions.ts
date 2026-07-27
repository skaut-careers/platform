export type DecisionType = "prepare" | "queue" | "escalate" | "skip";

export type DecisionCopy = {
  label: string;
  parts: [string, string];
};

/** Short one-line match copy — two beats for every decision. */
export const DECISION_COPY: Record<DecisionType, DecisionCopy> = {
  prepare: {
    label: "PREPARE",
    parts: ["strong fit", "go ahead and apply"],
  },
  queue: {
    label: "QUEUE",
    parts: ["some things mismatch", "better to come back later"],
  },
  escalate: {
    label: "ESCALATE",
    parts: ["too unclear to judge", "inspect it personally"],
  },
  skip: {
    label: "SKIP",
    parts: ["poor fit", "let it go"],
  },
};
