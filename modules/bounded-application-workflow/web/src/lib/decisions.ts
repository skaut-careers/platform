export type DecisionType = "strong" | "prepare" | "queue" | "skip";

export type DecisionCopy = {
  label: string;
  parts: [string, string];
};

/** Short one-line match copy — two beats for every decision. */
export const DECISION_COPY: Record<DecisionType, DecisionCopy> = {
  strong: {
    label: "STRONG",
    parts: ["excellent fit", "apply now"],
  },
  prepare: {
    label: "PREPARE",
    parts: ["good fit", "worth pursuing"],
  },
  queue: {
    label: "QUEUE",
    parts: ["some things mismatch", "better to come back later"],
  },
  skip: {
    label: "SKIP",
    parts: ["poor fit", "let it go"],
  },
};
