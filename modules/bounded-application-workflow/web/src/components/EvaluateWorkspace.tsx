"use client";

import Image from "next/image";
import { useRef, useState } from "react";

import { Atmosphere } from "@/components/Atmosphere";
import {
  EMPTY_PROFILE,
  WORK_PREFERENCE_OPTIONS,
  type ProfileFormValues,
} from "@/lib/examples";
import { DECISION_COPY } from "@/lib/decisions";

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

function parseList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function validateProfile(profile: ProfileFormValues): string[] {
  const errors: string[] = [];
  if (parseList(profile.targetRoles).length < 1) errors.push("Add at least 1 role.");
  if (parseList(profile.skills).length < 3) errors.push("Add at least 3 skills.");
  if (!profile.seniority.trim()) errors.push("Add seniority.");
  if (profile.workPreferences.length < 1) {
    errors.push("Pick at least one work preference.");
  }
  return errors;
}

function validateJob(jobText: string): string[] {
  if (jobText.trim().length < 40) {
    return ["Paste a fuller job description (~40+ characters)."];
  }
  return [];
}

const STEPS = [
  { id: 1 as const, label: "You" },
  { id: 2 as const, label: "Role" },
  { id: 3 as const, label: "Match" },
];

export function EvaluateWorkspace() {
  const [profile, setProfile] = useState<ProfileFormValues>(EMPTY_PROFILE);
  const [jobText, setJobText] = useState("");
  const [step, setStep] = useState<Step>(1);
  const [showPlaceholder, setShowPlaceholder] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const productRef = useRef<HTMLHeadingElement | null>(null);

  function updateProfile<K extends keyof ProfileFormValues>(
    key: K,
    value: ProfileFormValues[K],
  ) {
    setProfile((current) => ({ ...current, [key]: value }));
  }

  function toggleWorkPreference(option: string) {
    setProfile((current) => {
      const selected = current.workPreferences.includes(option)
        ? current.workPreferences.filter((item) => item !== option)
        : [...current.workPreferences, option];
      return { ...current, workPreferences: selected };
    });
  }

  function scrollToProduct() {
    productRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function goToRole() {
    const nextErrors = validateProfile(profile);
    setErrors(nextErrors);
    if (nextErrors.length > 0) return;
    setErrors([]);
    setStep(2);
  }

  function onEvaluate() {
    const nextErrors = [...validateProfile(profile), ...validateJob(jobText)];
    setErrors(nextErrors);
    if (nextErrors.length > 0) return;
    setShowPlaceholder(true);
    setStep(3);
  }

  // Trail dots navigate backward only; forward moves go through the step buttons.
  function goToStep(next: Step) {
    if (next >= step) return;
    setErrors([]);
    setStep(next);
  }

  function checkAnotherRole() {
    setJobText("");
    setShowPlaceholder(false);
    setErrors([]);
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
        id="evaluate"
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

            <div className="panel-body mt-3">
              <div className="grid grid-cols-2 gap-x-3 gap-y-2 md:grid-cols-4">
                <label className="flex flex-col gap-1">
                  <span className={labelClassName}>
                    Level
                    <RequiredMark />
                  </span>
                  <input
                    value={profile.seniority}
                    onChange={(event) => updateProfile("seniority", event.target.value)}
                    placeholder="mid…"
                    className={fieldClassName}
                    required
                    tabIndex={step === 1 ? 0 : -1}
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className={labelClassName}>Base</span>
                  <input
                    value={profile.location}
                    onChange={(event) => updateProfile("location", event.target.value)}
                    placeholder="city"
                    className={fieldClassName}
                    tabIndex={step === 1 ? 0 : -1}
                  />
                </label>
                <label className="col-span-2 flex flex-col gap-1">
                  <span className={labelClassName}>
                    Roles you want
                    <RequiredMark />
                  </span>
                  <input
                    value={profile.targetRoles}
                    onChange={(event) => updateProfile("targetRoles", event.target.value)}
                    placeholder="AI Engineer, Backend…"
                    className={fieldClassName}
                    required
                    tabIndex={step === 1 ? 0 : -1}
                  />
                </label>
                <label className="col-span-2 flex flex-col gap-1">
                  <span className={labelClassName}>
                    Skills
                    <RequiredMark />
                  </span>
                  <input
                    value={profile.skills}
                    onChange={(event) => updateProfile("skills", event.target.value)}
                    placeholder="Python, SQL, system design"
                    className={fieldClassName}
                    required
                    tabIndex={step === 1 ? 0 : -1}
                  />
                </label>
                <label className="col-span-2 flex flex-col gap-1">
                  <span className={labelClassName}>Recent wins</span>
                  <input
                    value={profile.experienceSummary}
                    onChange={(event) =>
                      updateProfile("experienceSummary", event.target.value)
                    }
                    placeholder="What you’ve shipped lately"
                    className={fieldClassName}
                    tabIndex={step === 1 ? 0 : -1}
                  />
                </label>
                <label className="col-span-2 flex flex-col gap-1">
                  <span className={labelClassName}>Production (optional)</span>
                  <input
                    value={profile.productionExperience}
                    onChange={(event) =>
                      updateProfile("productionExperience", event.target.value)
                    }
                    placeholder="on-call, owned services…"
                    className={fieldClassName}
                    tabIndex={step === 1 ? 0 : -1}
                  />
                </label>
              </div>

              <div className="mt-3">
                <span className={labelClassName}>
                  Where you work best (select all that apply)
                  <RequiredMark />
                </span>
                <div className="mt-1.5 flex flex-wrap gap-2">
                  {WORK_PREFERENCE_OPTIONS.map((option) => {
                    const selected = profile.workPreferences.includes(option);
                    return (
                      <button
                        key={option}
                        type="button"
                        onClick={() => toggleWorkPreference(option)}
                        className={`choice-chip capitalize ${selected ? "is-on" : ""}`}
                        tabIndex={step === 1 ? 0 : -1}
                      >
                        {option}
                      </button>
                    );
                  })}
                </div>
              </div>
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
                  required
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
                onClick={onEvaluate}
                className="quest-btn panel-action"
                tabIndex={step === 2 ? 0 : -1}
              >
                Check match →
              </button>
            </div>
          </div>

          <div
            className={`quest-panel panel-stage-item ${step === 3 ? "is-shown" : ""}`}
            aria-hidden={step !== 3}
          >
            <div className="quest-badge">Stop 3</div>

            <div className="panel-body mt-3 items-center justify-center text-center">
              {showPlaceholder ? (
                <div className="flex max-w-lg flex-col items-center gap-3 px-4">
                  <p className="font-display text-4xl font-semibold tracking-tight text-forest md:text-5xl">
                    {DECISION_COPY.queue.label}
                  </p>
                  <p className="whitespace-nowrap text-sm leading-7 tracking-wide text-muted">
                    {DECISION_COPY.queue.parts.map((part, index) => (
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
