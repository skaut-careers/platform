export type ProfileFormValues = {
  targetRoles: string;
  skills: string;
  experienceSummary: string;
  location: string;
  seniority: string;
  productionExperience: string;
  workPreferences: string[];
};

export const WORK_PREFERENCE_OPTIONS = [
  "remote",
  "hybrid",
  "onsite",
] as const;

/** Default empty profile for the product form. */
export const EMPTY_PROFILE: ProfileFormValues = {
  targetRoles: "",
  skills: "",
  experienceSummary: "",
  location: "",
  seniority: "",
  productionExperience: "",
  workPreferences: [],
};

/** Concatenate form fields into the raw `profile_text` the workflow expects. */
export function toProfileText(profile: ProfileFormValues): string {
  return [
    `target_roles: ${profile.targetRoles.trim()}`,
    `skills: ${profile.skills.trim()}`,
    `seniority: ${profile.seniority.trim()}`,
    `location: ${profile.location.trim()}`,
    `experience_summary: ${profile.experienceSummary.trim()}`,
    `work_preferences: ${profile.workPreferences.join(", ")}`,
    `production_experience: ${profile.productionExperience.trim()}`,
  ].join("\n");
}
