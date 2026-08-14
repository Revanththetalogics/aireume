export const DEFAULT_WEIGHTS = {
  core_competencies: 0.30,
  experience: 0.20,
  domain_fit: 0.20,
  education: 0.10,
  career_trajectory: 0.10,
  role_excellence: 0.10,
  risk: -0.10,
}

export const WEIGHT_PRESETS = {
  balanced: { core_competencies: 0.30, experience: 0.20, domain_fit: 0.20, education: 0.10, career_trajectory: 0.10, role_excellence: 0.10, risk: -0.10 },
  'skill-heavy': { core_competencies: 0.40, experience: 0.20, domain_fit: 0.15, education: 0.05, career_trajectory: 0.10, role_excellence: 0.10, risk: -0.10 },
  'experience-heavy': { core_competencies: 0.25, experience: 0.35, domain_fit: 0.15, education: 0.05, career_trajectory: 0.10, role_excellence: 0.10, risk: -0.10 },
  'domain-focused': { core_competencies: 0.25, experience: 0.20, domain_fit: 0.30, education: 0.05, career_trajectory: 0.10, role_excellence: 0.10, risk: -0.10 },
}

export const PRESET_LABELS = {
  balanced: 'Balanced',
  'skill-heavy': 'Skill-Heavy',
  'experience-heavy': 'Experience-Heavy',
  'domain-focused': 'Domain-Focused',
}

export const BACKGROUND_BATCH_MIN = 20
export const BACKGROUND_BATCH_AUTO = 50
