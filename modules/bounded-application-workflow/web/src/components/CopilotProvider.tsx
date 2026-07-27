"use client";

type CopilotProviderProps = {
  children: React.ReactNode;
};

/**
 * Passthrough shell for #69.
 * Real CopilotKit wiring (no floating chat UI) comes in later issues.
 */
export function CopilotProvider({ children }: CopilotProviderProps) {
  return <>{children}</>;
}
