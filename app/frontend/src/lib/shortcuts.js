/**
 * Keyboard shortcut definitions for ARIA platform.
 * Each shortcut has: key, description, scope (where it's active)
 */
export const SHORTCUTS = {
  SHORTLIST: { key: 's', description: 'Shortlist selected candidate', scope: 'candidates' },
  REJECT: { key: 'r', description: 'Reject selected candidate', scope: 'candidates' },
  NEXT: { key: 'j', description: 'Select next candidate', scope: 'candidates' },
  PREV: { key: 'k', description: 'Select previous candidate', scope: 'candidates' },
  SEARCH: { key: 'k', meta: true, description: 'Focus search', scope: 'global' },
  OPEN: { key: 'Enter', description: 'Open selected candidate', scope: 'candidates' },
};
