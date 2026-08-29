/**
 * Verified-only filter + builtin fallback rules.
 *
 * Product lock: the marketplace must not present hardcoded builtins as
 * marketplace-approved. `?verified=0` unchecks; anything else (including
 * a missing param) stays checked. No localStorage.
 */

/** Builtins are never marketplace-approved. Do not use `'verified'`. */
export const BUILTIN_VERIFICATION_STATUS = 'unverified' as const;
export const BUILTIN_VERIFICATION_NOTES =
  'Built-in catalog (not marketplace-verified)';

/**
 * Default is checked (true). Only an explicit `?verified=0` unchecks.
 * `?verified=1` stays checked.
 */
export function parseVerifiedOnlyParam(
  value: string | null | undefined,
): boolean {
  return value !== '0';
}

/** Persist the toggle in the URL so reload does not surprise the user. */
export function setVerifiedOnlySearchParam(
  params: URLSearchParams,
  verifiedOnly: boolean,
): void {
  if (verifiedOnly) params.set('verified', '1');
  else params.set('verified', '0');
}

/**
 * When the canister returned listings, use those.
 * When it is empty or errored: prefer an empty list under verified-only
 * (do not fake Verified). If the user asked for everything, builtins may
 * remain for offline/dev — callers must not mark them `'verified'`.
 */
export function listingsOrBuiltinFallback<T>(
  canisterListings: readonly T[] | null | undefined,
  builtins: readonly T[],
  verifiedOnly: boolean,
): T[] {
  if (canisterListings && canisterListings.length > 0) {
    return [...canisterListings];
  }
  if (verifiedOnly) return [];
  return [...builtins];
}

export function paginateList<T>(
  items: readonly T[],
  page: number,
  perPage: number,
): { listings: T[]; total_count: number; page: number; per_page: number } {
  const safePage = Number.isFinite(page) && page > 0 ? page : 1;
  const safePer = Number.isFinite(perPage) && perPage > 0 ? perPage : 1;
  const start = (safePage - 1) * safePer;
  return {
    listings: items.slice(start, start + safePer),
    total_count: items.length,
    page: safePage,
    per_page: safePer,
  };
}

export function isMarketplaceVerified(status: string | null | undefined): boolean {
  return status === 'verified';
}
