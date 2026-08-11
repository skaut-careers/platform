"use client";

import Image from "next/image";
import { useRef, useState } from "react";
import { randomUUID } from "@ag-ui/client";
import { useAgent, UseAgentUpdate } from "@copilotkit/react-core/v2";

import { Atmosphere } from "@/components/Atmosphere";
import { MatchResult } from "@/components/MatchResult";
import {
  WORKFLOW_AGENT_ID,
  missingSignals,
  stageProgressLabel,
  workflowDecision,
  type WorkflowAgentState,
} from "@/lib/workflow";

const fieldClassName =
  "w-full rounded-lg border border-line bg-surface/90 px-3 py-2.5 text-sm text-ink outline-none transition placeholder:text-muted/50 focus:border-forest focus:ring-2 focus:ring-forest/15";

const labelClassName = "text-xs font-medium text-muted";

function RequiredMark() {
  return (
    <span className="ml-0.5 text-[#b42318]" aria-hidden>
      *
    </span>
  );
}

type Step = 1 | 2 | 3;

function validatePaste(text: string, label: string): string[] {
  if (text.trim().length < 40) {
    return [`Paste a fuller ${label} (~40+ characters).`];
  }
  return [];
}

const STEPS = [
  { id: 1 as const, label: "You" },
  { id: 2 as const, label: "Role" },
  { id: 3 as const, label: "Match" },
];

export function RunWorkspace() {
  const [profileText, setProfileText] = useState("");
  const [jobText, setJobText] = useState("");
  const [step, setStep] = useState<Step>(1);
  const [errors, setErrors] = useState<string[]>([]);
  const [runError, setRunError] = useState<string | null>(null);
  const [hasStartedRun, setHasStartedRun] = useState(false);
  const productRef = useRef<HTMLHeadingElement | null>(null);

  const { agent } = useAgent({
    agentId: WORKFLOW_AGENT_ID,
    updates: [UseAgentUpdate.OnStateChanged, UseAgentUpdate.OnRunStatusChanged],
  });

  const state = (agent.state ?? {}) as WorkflowAgentState;
  const decision = workflowDecision(state);
  const running = agent.isRunning;

  function scrollToProduct() {
    productRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function goToRole() {
    const nextErrors = validatePaste(profileText, "CV");
    setErrors(nextErrors);
    if (nextErrors.length > 0) return;
    setErrors([]);
    setStep(2);
  }

  async function onRun() {
    const nextErrors = [
      ...validatePaste(profileText, "CV"),
      ...validatePaste(jobText, "job description"),
    ];
    setErrors(nextErrors);
    if (nextErrors.length > 0) return;

    setRunError(null);
    setHasStartedRun(true);
    setStep(3);

    agent.threadId = randomUUID();
    agent.setState({
      profile_text: profileText.trim(),
      job_description_text: jobText.trim(),
    });

    try {
      await agent.runAgent();
      if (!workflowDecision(agent.state as WorkflowAgentState)) {
        setRunError("No decision returned. Try again or pick another role.");
      }
    } catch (error) {
      setRunError(error instanceof Error ? error.message : "Workflow failed.");
    }
  }

  // Trail dots navigate backward only; forward moves go through the step buttons.
  function goToStep(next: Step) {
    if (next >= step) return;
    setErrors([]);
    setStep(next);
  }

  function checkAnotherRole() {
    if (running) agent.abortRun();
    setJobText("");
    setErrors([]);
    setRunError(null);
    setHasStartedRun(false);
    agent.setState({});
    setStep(2);
  }

  return (
    <div className="relative min-h-screen overflow-x-hidden">
      <Atmosphere />

      <section className="relative flex min-h-[100svh] flex-col items-center justify-center px-6 text-center">
        <div className="soft-rise flex max-w-4xl flex-col items-center">
          <Image
            src="/logo.svg"
            alt="Skaut Careers"
            width={120}
            height={120}
            className="object-contain"
            priority
          />
          <h1 className="font-display mt-6 text-6xl font-semibold tracking-tight text-forest md:text-7xl lg:text-8xl">
            Skaut Careers
          </h1>
          <p className="mt-4 text-xl text-ink md:text-2xl">
            Navigate your professional life with clarity.
          </p>
        </div>

        <button
          type="button"
          onClick={scrollToProduct}
          className="scroll-cue absolute bottom-8 flex flex-col items-center gap-2 text-sm font-medium text-muted transition hover:text-forest"
        >
          <span>Try our first feature</span>
          <span aria-hidden className="text-lg leading-none">
            ↓
          </span>
        </button>
      </section>

      <div aria-hidden className="h-28 md:h-40" />

      <section
        id="workflow"
        className="relative mx-auto flex w-full max-w-3xl flex-col gap-6 px-5 pb-16"
      >
        <div className="text-center">
          <h2
            ref={productRef}
            className="font-display scroll-mt-6 text-3xl font-semibold tracking-tight text-forest md:text-4xl"
          >
            Is this role worth applying for?
          </h2>
          <p className="mt-2 text-sm text-muted">Three quick stops on the trail.</p>
        </div>

        <ol className="trail-progress" aria-label="Progress">
          {STEPS.map((item, index) => {
            const active = step === item.id;
            const done = step > item.id;
            const canJump = item.id < step;
            return (
              <li key={item.id} className="contents">
                {index > 0 ? (
                  <span
                    aria-hidden
                    className={`trail-line ${done || active ? "is-lit" : ""}`}
                  />
                ) : null}
                <button
                  type="button"
                  disabled={!canJump}
                  onClick={() => goToStep(item.id)}
                  className={`trail-stop ${active ? "is-active" : ""} ${done ? "is-done" : ""} ${canJump ? "is-clickable" : ""}`}
                  aria-current={active ? "step" : undefined}
                  aria-label={`Go to ${item.label}`}
                >
                  <span className="trail-dot">{done ? "✓" : item.id}</span>
                  <span className="trail-label">{item.label}</span>
                </button>
              </li>
            );
          })}
        </ol>

        <div className="panel-stage">
          <div
            className={`quest-panel panel-stage-item ${step === 1 ? "is-shown" : ""}`}
            aria-hidden={step !== 1}
          >
            <div className="quest-badge">Stop 1</div>
            <h3 className="font-display text-2xl font-semibold text-forest">You</h3>
            <p className="mt-1 text-sm text-muted">
              Paste your CV — we extract roles, skills, and preferences from it.
            </p>

            <div className="panel-body mt-3">
              <label className="flex h-full min-h-0 flex-col gap-1">
                <span className={labelClassName}>
                  CV
                  <RequiredMark />
                </span>
                <textarea
                  value={profileText}
                  onChange={(event) => setProfileText(event.target.value)}
                  placeholder="Paste your CV…"
                  className={`${fieldClassName} min-h-[10.5rem] flex-1 resize-y leading-6`}
                  tabIndex={step === 1 ? 0 : -1}
                />
              </label>
            </div>

            <div className="panel-footer">
              {step === 1 && errors.length > 0 ? (
                <ul className="text-sm text-[#8a3b2a]">
                  {errors.map((error) => (
                    <li key={error}>{error}</li>
                  ))}
                </ul>
              ) : (
                <span />
              )}
              <button
                type="button"
                onClick={goToRole}
                className="quest-btn panel-action"
                tabIndex={step === 1 ? 0 : -1}
              >
                Next stop · the role →
              </button>
            </div>
          </div>

          <div
            className={`quest-panel panel-stage-item ${step === 2 ? "is-shown" : ""}`}
            aria-hidden={step !== 2}
          >
            <div className="quest-badge">Stop 2</div>
            <h3 className="font-display text-2xl font-semibold text-forest">The role</h3>

            <div className="panel-body mt-3">
              <label className="flex h-full min-h-0 flex-col gap-1">
                <span className={labelClassName}>
                  Job posting
                  <RequiredMark />
                </span>
                <textarea
                  value={jobText}
                  onChange={(event) => setJobText(event.target.value)}
                  placeholder="Paste the job posting…"
                  className={`${fieldClassName} min-h-[10.5rem] flex-1 resize-y leading-6`}
                  tabIndex={step === 2 ? 0 : -1}
                />
              </label>
            </div>

            <div className="panel-footer">
              {step === 2 && errors.length > 0 ? (
                <ul className="text-sm text-[#8a3b2a]">
                  {errors.map((error) => (
                    <li key={error}>{error}</li>
                  ))}
                </ul>
              ) : (
                <span />
              )}
              <button
                type="button"
                onClick={() => void onRun()}
                className="quest-btn panel-action"
                disabled={running}
                tabIndex={step === 2 ? 0 : -1}
              >
                {running ? "Checking…" : "Check match →"}
              </button>
            </div>
          </div>

          <div
            className={`quest-panel panel-stage-item ${step === 3 ? "is-shown" : ""}`}
            aria-hidden={step !== 3}
          >
            <div className="quest-badge">Stop 3</div>

            <div className="panel-body mt-3 items-center justify-center text-center">
              {running ? (
                <div className="flex flex-col items-center gap-2 px-4">
                  <p className="font-display text-2xl font-semibold text-forest">
                    Checking match
                  </p>
                  <p className="text-sm text-muted" aria-live="polite">
                    {stageProgressLabel(state)}
                  </p>
                </div>
              ) : runError ? (
                <p className="max-w-md text-sm text-[#8a3b2a]" role="alert">
                  {runError}
                </p>
              ) : decision ? (
                <MatchResult
                  decision={decision}
                  missingSignals={missingSignals(state)}
                />
              ) : hasStartedRun ? (
                <p className="text-sm text-muted">No result yet.</p>
              ) : (
                <p className="text-sm text-muted">Run a check to see your match.</p>
              )}
            </div>

            <div className="panel-footer">
              <span />
              <button
                type="button"
                onClick={checkAnotherRole}
                className="quest-btn panel-action"
                disabled={running}
                tabIndex={step === 3 ? 0 : -1}
              >
                Check another role →
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
