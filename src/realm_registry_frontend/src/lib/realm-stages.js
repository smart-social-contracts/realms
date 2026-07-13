/** Realm lifecycle stages — shared labels and colors across browse UI. */

export const REALM_STAGES = [
  { id: 'alpha', label: 'Alpha', color: '#06b6d4', bg: 'rgba(6, 182, 212, 0.14)' },
  { id: 'beta', label: 'Beta', color: '#ca8a04', bg: 'rgba(234, 179, 8, 0.18)' },
  { id: 'production', label: 'Live', color: '#16a34a', bg: 'rgba(34, 197, 94, 0.14)' },
  { id: 'deprecation', label: 'Winding Down', color: '#ea580c', bg: 'rgba(249, 115, 22, 0.14)' },
  { id: 'terminated', label: 'Archived', color: '#dc2626', bg: 'rgba(239, 68, 68, 0.14)' },
];

/** @param {string | undefined | null} stageId */
export function stageMeta(stageId) {
  if (!stageId) return null;
  return REALM_STAGES.find((stage) => stage.id === stageId) ?? null;
}

/** @param {string | undefined | null} stageId */
export function stageLabel(stageId) {
  return stageMeta(stageId)?.label ?? 'Alpha';
}
