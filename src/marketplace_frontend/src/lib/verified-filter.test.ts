import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import {
  BUILTIN_VERIFICATION_NOTES,
  BUILTIN_VERIFICATION_STATUS,
  isMarketplaceVerified,
  listingsOrBuiltinFallback,
  paginateList,
  parseVerifiedOnlyParam,
  setVerifiedOnlySearchParam,
} from './verified-filter.ts';

describe('parseVerifiedOnlyParam', () => {
  it('defaults to true when the param is missing', () => {
    assert.equal(parseVerifiedOnlyParam(null), true);
    assert.equal(parseVerifiedOnlyParam(undefined), true);
    assert.equal(parseVerifiedOnlyParam(''), true);
  });

  it('stays checked for ?verified=1', () => {
    assert.equal(parseVerifiedOnlyParam('1'), true);
  });

  it('unchecks only for ?verified=0', () => {
    assert.equal(parseVerifiedOnlyParam('0'), false);
  });
});

describe('setVerifiedOnlySearchParam', () => {
  it('writes verified=1 when checked and verified=0 when unchecked', () => {
    const on = new URLSearchParams();
    setVerifiedOnlySearchParam(on, true);
    assert.equal(on.get('verified'), '1');

    const off = new URLSearchParams();
    setVerifiedOnlySearchParam(off, false);
    assert.equal(off.get('verified'), '0');
  });
});

describe('listingsOrBuiltinFallback', () => {
  const builtins = [
    { id: 'hello_world', verification_status: BUILTIN_VERIFICATION_STATUS },
    { id: 'voting', verification_status: BUILTIN_VERIFICATION_STATUS },
  ];
  const canister = [{ id: 'real-ext', verification_status: 'verified' }];

  it('returns canister listings when present', () => {
    assert.deepEqual(
      listingsOrBuiltinFallback(canister, builtins, true),
      canister,
    );
  });

  it('does not serve builtins as marketplace-verified when the canister is empty', () => {
    const emptyVerified = listingsOrBuiltinFallback([], builtins, true);
    assert.deepEqual(emptyVerified, []);
    assert.ok(emptyVerified.every((item) => !isMarketplaceVerified(item.verification_status)));

    const erroredVerified = listingsOrBuiltinFallback(null, builtins, true);
    assert.deepEqual(erroredVerified, []);
  });

  it('may return builtins for offline/dev only when verified-only is off, never as verified', () => {
    const items = listingsOrBuiltinFallback([], builtins, false);
    assert.equal(items.length, builtins.length);
    for (const item of items) {
      assert.notEqual(item.verification_status, 'verified');
      assert.equal(isMarketplaceVerified(item.verification_status), false);
    }
  });
});

describe('builtin verification lock', () => {
  it('does not treat the builtin status as marketplace-verified', () => {
    assert.notEqual(BUILTIN_VERIFICATION_STATUS, 'verified');
    assert.equal(isMarketplaceVerified(BUILTIN_VERIFICATION_STATUS), false);
    assert.match(BUILTIN_VERIFICATION_NOTES, /not marketplace-verified/i);
  });
});

describe('builtin catalog factories', () => {
  it('do not hardcode marketplace-verified on fallback cards', async () => {
    const { readFileSync } = await import('node:fs');
    const { dirname, join } = await import('node:path');
    const { fileURLToPath } = await import('node:url');
    const src = readFileSync(
      join(dirname(fileURLToPath(import.meta.url)), 'builtin-catalog.ts'),
      'utf8',
    );
    assert.equal(src.includes("verification_status: 'verified'"), false);
    assert.ok(src.includes('BUILTIN_VERIFICATION_STATUS'));

    const client = readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'marketplace-client.ts'), 'utf8');
    assert.ok(client.includes('listingsOrBuiltinFallback'));
    assert.equal(/return builtinExtensions\.slice/.test(client), false);
    assert.equal(/return builtinCodices\.slice/.test(client), false);

    const routesDir = join(dirname(fileURLToPath(import.meta.url)), '../routes');
    const routeFiles = [
      join(routesDir, '+page.svelte'),
      join(routesDir, 'extensions/+page.svelte'),
      join(routesDir, 'codices/+page.svelte'),
      join(routesDir, 'assistants/+page.svelte'),
    ];
    for (const file of routeFiles) {
      const page = readFileSync(file, 'utf8');
      assert.ok(page.includes('let verifiedOnly = true'), file);
      assert.equal(page.includes('let verifiedOnly = false'), false, file);
    }
  });
});

describe('paginateList', () => {
  it('pages a fallback list without inventing verified rows', () => {
    const items = listingsOrBuiltinFallback([], [{ id: 'a' }, { id: 'b' }], false);
    const page = paginateList(items, 1, 1);
    assert.equal(page.total_count, 2);
    assert.equal(page.listings.length, 1);
  });
});
