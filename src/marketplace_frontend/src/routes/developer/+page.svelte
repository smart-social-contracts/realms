<script lang="ts">
  import VerifiedBadge from '$lib/components/VerifiedBadge.svelte';
  import Spinner from '$lib/components/Spinner.svelte';
  import { isAuthenticated, principalStore } from '$lib/auth';
  import { CONFIG } from '$lib/config';
  import { marketplaceClient, type DeveloperLicense, type ExtensionListing, type CodexListing } from '$lib/marketplace-client';
  import { formatTimeAgo, formatCount, formatPriceUsd } from '$lib/format';

  let loading = false;
  let error = '';
  let license: DeveloperLicense | null = null;
  let pricing = { license_price_usd_cents: 0, license_duration_seconds: 0 };
  let myExtensions: ExtensionListing[] = [];
  let myCodices: CodexListing[] = [];
  let buyingLicense = false;
  let licenseError = '';

  $: void load($isAuthenticated);

  async function load(_authed: boolean) {
    if (!_authed) {
      license = null;
      myExtensions = [];
      myCodices = [];
      return;
    }
    loading = true;
    error = '';
    try {
      pricing = await marketplaceClient.getLicensePricing();
      license = await marketplaceClient.getLicenseStatus();
      myExtensions = await marketplaceClient.getMyExtensions();
      myCodices = await marketplaceClient.getMyCodices();
    } catch (e: any) {
      error = e?.message ?? String(e);
    } finally {
      loading = false;
    }
  }

  async function buyLicense() {
    if (buyingLicense || !$principalStore) return;
    buyingLicense = true;
    licenseError = '';
    try {
      const url = `${CONFIG.billing_service_url.replace(/\/$/, '')}/marketplace/license/checkout`;
      const returnUrl = `${window.location.origin}/developer?license_status=success`;
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          principal_id: $principalStore.toText(),
          return_url: returnUrl,
          marketplace_canister_id: CONFIG.marketplace_canister_id,
        }),
      });
      if (!resp.ok) {
        const txt = await resp.text().catch(() => '');
        throw new Error(`HTTP ${resp.status}${txt ? `: ${txt}` : ''}`);
      }
      const data = await resp.json();
      if (!data.checkout_url) throw new Error('billing service returned no checkout_url');
      window.location.href = data.checkout_url;
    } catch (e: any) {
      // Graceful "Service unavailable" degradation — keep the user in
      // the marketplace UI with a clear next step (controller can grant
      // a manual license via /admin during local dev or before the
      // billing service is up).
      licenseError =
        `Billing service unavailable: ${e?.message ?? e}. ` +
        `If you're running locally, ask a controller to grant a manual license from /admin.`;
    } finally {
      buyingLicense = false;
    }
  }

  async function requestAuditFor(kind: 'ext' | 'codex', id: string) {
    try {
      await marketplaceClient.requestAudit(kind, id);
      await load(true);
    } catch (e: any) {
      alert(`Could not request audit: ${e?.message ?? e}`);
    }
  }

  async function delist(kind: 'ext' | 'codex', id: string) {
    if (!confirm(`Delist ${kind} '${id}'?`)) return;
    try {
      if (kind === 'ext') await marketplaceClient.delistExtension(id);
      else await marketplaceClient.delistCodex(id);
      await load(true);
    } catch (e: any) {
      alert(`Could not delist: ${e?.message ?? e}`);
    }
  }
</script>

<header class="head">
  <h1>Developer</h1>
  <p>License status, your published items, and audit requests.</p>
</header>

{#if !$isAuthenticated}
  <div class="card warn">
    <h2>Sign in required</h2>
    <p>Sign in with Internet Identity to manage your listings.</p>
  </div>
{:else if loading}
  <div class="state"><Spinner /></div>
{:else if error}
  <div class="state error">⚠️ {error}</div>
{:else}
  <section class="card">
    <h2>Developer license</h2>
    {#if license && license.is_active}
      <p class="ok">
        ✅ Active until <strong>{new Date(license.expires_at / 1_000_000).toLocaleString()}</strong>
        {#if license.payment_method}<span class="muted"> — paid via {license.payment_method}</span>{/if}
      </p>
      <p class="small">
        License grants you access to the audit flow. Anyone can publish without one.
      </p>
    {:else}
      <p>No active license.</p>
      <ul class="benefits">
        <li>Get audited and approved by Smart Social Contracts</li>
        <li>Show a "Verified" badge on your listings</li>
        <li>Surface in the verified-only filters and rankings</li>
      </ul>
      <p class="price">
        {formatPriceUsd(pricing.license_price_usd_cents)} / year
      </p>
      <button class="btn primary" disabled={buyingLicense} on:click={buyLicense}>
        {buyingLicense ? 'Redirecting…' : 'Pay with credit card →'}
      </button>
      {#if licenseError}
        <p class="license-error">⚠️ {licenseError}</p>
      {/if}
      <p class="small muted">
        Powered by the off-chain billing service at <code>{CONFIG.billing_service_url}</code>.
        Local dev tip: ask a controller to call <code>grant_manual_license</code>.
      </p>
    {/if}
  </section>

  <section class="card">
    <h2>My extensions ({myExtensions.length})</h2>
    {#if myExtensions.length === 0}
      <p class="muted">You haven't published any extensions yet. <a href="/upload">Upload one →</a></p>
    {:else}
      <table>
        <thead><tr><th>Id</th><th>Version</th><th>Verified</th><th>Installs</th><th>Likes</th><th>Updated</th><th></th></tr></thead>
        <tbody>
          {#each myExtensions as e}
            <tr>
              <td><a class="link" href={`/extensions/${encodeURIComponent(e.extension_id)}`}>{e.extension_id}</a></td>
              <td>{e.version}</td>
              <td><VerifiedBadge status={e.verification_status} /></td>
              <td>{formatCount(e.installs)}</td>
              <td>{formatCount(e.likes)}</td>
              <td>{formatTimeAgo(e.updated_at)}</td>
              <td>
                <button class="btn tiny" disabled={e.verification_status === 'pending_audit' || e.verification_status === 'verified'} on:click={() => requestAuditFor('ext', e.extension_id)}>
                  Request audit
                </button>
                <button class="btn tiny ghost" on:click={() => delist('ext', e.extension_id)}>Delist</button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </section>

  <section class="card">
    <h2>My codices ({myCodices.length})</h2>
    {#if myCodices.length === 0}
      <p class="muted">You haven't published any codices yet. <a href="/upload">Upload one →</a></p>
    {:else}
      <table>
        <thead><tr><th>Id</th><th>Version</th><th>Verified</th><th>Installs</th><th>Likes</th><th>Updated</th><th></th></tr></thead>
        <tbody>
          {#each myCodices as c}
            <tr>
              <td><a class="link" href={`/codices/${encodeURIComponent(c.codex_id)}`}>{c.codex_id}</a></td>
              <td>{c.version}</td>
              <td><VerifiedBadge status={c.verification_status} /></td>
              <td>{formatCount(c.installs)}</td>
              <td>{formatCount(c.likes)}</td>
              <td>{formatTimeAgo(c.updated_at)}</td>
              <td>
                <button class="btn tiny" disabled={c.verification_status === 'pending_audit' || c.verification_status === 'verified'} on:click={() => requestAuditFor('codex', c.codex_id)}>
                  Request audit
                </button>
                <button class="btn tiny ghost" on:click={() => delist('codex', c.codex_id)}>Delist</button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </section>
{/if}

<style>
  .head h1 { margin: 0 0 0.25rem; font-size: 1.8rem; }
  .head p { margin: 0 0 1.5rem; color: var(--text-muted); }
  .card {
    background: var(--surface); border: 1px solid var(--border);
    padding: 1.5rem 1.75rem; border-radius: 0.75rem; margin-bottom: 1.25rem;
  }
  .card.warn { border-color: var(--warning); background: #FEF3C7; color: #92400E; }
  .card h2 { margin: 0 0 0.85rem; font-size: 1.1rem; }
  .ok { color: var(--success); font-weight: 500; }
  .price { font-size: 1.5rem; font-weight: 700; margin: 0.85rem 0; color: var(--text); }
  .license-error {
    margin: 0.75rem 0 0;
    padding: 0.65rem 0.85rem;
    background: #FEE2E2;
    border: 1px solid var(--danger);
    color: #991B1B;
    border-radius: 0.5rem;
    font-size: 0.85rem;
  }
  .benefits { margin: 0.5rem 0 0.85rem 1.25rem; color: var(--text-muted); }
  .small { font-size: 0.8rem; }
  .muted { color: var(--text-faint); }
  .btn {
    border: 1px solid var(--border); background: var(--surface); color: var(--text-muted);
    padding: 0.5rem 1rem; border-radius: 0.4rem;
  }
  .btn:hover:not(:disabled) { background: var(--surface-2); color: var(--text); }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn.primary { background: var(--primary); border-color: var(--primary); color: #fff; }
  .btn.primary:hover:not(:disabled) { background: var(--primary-hover); }
  .btn.tiny { padding: 0.3rem 0.6rem; font-size: 0.75rem; margin-right: 0.3rem; }
  .btn.ghost { background: transparent; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 0.5rem; border-bottom: 1px solid var(--surface-2); font-size: 0.85rem; }
  th { color: var(--text-faint); font-weight: 500; }
  .link { color: var(--accent); }
  .state { text-align: center; padding: 3rem; color: var(--text-muted); }
  .state.error { color: var(--danger); }
</style>
