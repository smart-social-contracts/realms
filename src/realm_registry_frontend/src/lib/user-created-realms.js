/**
 * Resolve realms created by a user on the registry canister.
 *
 * Registry realm IDs are backend canister IDs (set during deploy registration),
 * not the user's Internet Identity principal.
 */

function realmVisitUrl(record) {
  const url = (record.url || record.backend_url || '').trim();
  if (url) return url.replace(/\/+$/, '') + '/';
  const fe = (record.frontend_canister_id || '').trim();
  if (fe) return `https://${fe}.icp0.io/`;
  return '';
}

function recordToRow(record) {
  return {
    id: record.id,
    name: record.name || record.id,
    url: realmVisitUrl(record),
    frontend_canister_id: record.frontend_canister_id || '',
  };
}

/** Collect backend canister IDs from completed deployment jobs owned by the user. */
export function backendIdsFromDeployments(deployments, principalText) {
  const ids = new Set();
  for (const d of deployments || []) {
    if ((d.caller_principal || '') !== principalText) continue;
    if ((d.raw_status || d.status || '').toLowerCase() !== 'completed') continue;
    const backendId = (d.backend_canister_id || '').trim();
    if (backendId) ids.add(backendId);
  }
  return ids;
}

/**
 * @param {string} principalText
 * @param {object[]} [deployments] - optional preloaded deployment rows
 * @returns {Promise<object[]>}
 */
export async function fetchCreatedRealmsForUser(principalText, deployments = null) {
  if (!principalText) return [];

  const { backend } = await import('$lib/canisters.js');
  const realmIds = new Set();

  // Legacy installs used the caller principal as realm id.
  realmIds.add(principalText);

  let rows = deployments;
  if (rows == null) {
    const { fetchDeploymentJobsFromInstaller } = await import('$lib/installer-queue.js');
    const jobs = await fetchDeploymentJobsFromInstaller();
    rows = jobs.filter((j) => (j.caller_principal || '') === principalText);
  }

  for (const id of backendIdsFromDeployments(rows, principalText)) {
    realmIds.add(id);
  }

  const found = new Map();
  for (const realmId of realmIds) {
    try {
      const result = await backend.get_realm(realmId);
      if (result?.Ok) {
        const row = recordToRow(result.Ok);
        found.set(row.id, row);
      }
    } catch {
      /* skip missing ids */
    }
  }

  return [...found.values()].sort((a, b) =>
    (a.name || '').localeCompare(b.name || '', undefined, { sensitivity: 'base' }),
  );
}
