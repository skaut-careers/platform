export type DemoProfile = {
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
export const EMPTY_PROFILE: DemoProfile = {
  targetRoles: "",
  skills: "",
  experienceSummary: "",
  location: "",
  seniority: "",
  productionExperience: "",
  workPreferences: [],
};
