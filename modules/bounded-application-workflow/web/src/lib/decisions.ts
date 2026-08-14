export type DecisionType = "prepare" | "queue" | "skip";

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
  skip: {
    label: "SKIP",
    parts: ["poor fit", "let it go"],
  },
};
