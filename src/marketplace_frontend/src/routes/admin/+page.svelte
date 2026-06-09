<script lang="ts">import { _ } from "svelte-i18n";
import Spinner from "$lib/components/Spinner.svelte";
import { isAuthenticated, principalStore } from "$lib/auth";
import { marketplaceClient } from "$lib/marketplace-client";
import { formatTimeAgo, shortPrincipal } from "$lib/format";
let status = null;
let pending = [];
let loading = false;
let error = "";
let grantPrincipal = "";
let grantDays = 365;
let grantNote = "manual grant";
$: void load($isAuthenticated);
async function load(_authed) {
  loading = true;
  error = "";
  try {
    status = await marketplaceClient.getStatus();
    if (status?.is_caller_controller) {
      pending = await marketplaceClient.listPendingAudits();
    }
  } catch (e) {
    error = e?.message ?? String(e);
  } finally {
    loading = false;
  }
}
async function approve(item) {
  const note = prompt($_("admin.curator_prompt"), "") ?? "";
  try {
    await marketplaceClient.setVerificationStatus(item.item_kind, item.item_id, "verified", note);
    await load(true);
  } catch (e) {
    alert($_("admin.approve_failed", { values: { error: e?.message ?? e } }));
  }
}
async function reject(item) {
  const note = prompt($_("admin.reject_prompt"), "") ?? "";
  try {
    await marketplaceClient.setVerificationStatus(item.item_kind, item.item_id, "rejected", note);
    await load(true);
  } catch (e) {
    alert($_("admin.reject_failed", { values: { error: e?.message ?? e } }));
  }
}
async function grantLicense() {
  if (!grantPrincipal.trim()) return;
  try {
    const seconds = Math.max(1, Math.round(grantDays * 86400));
    await marketplaceClient.grantManualLicense(grantPrincipal.trim(), seconds, grantNote);
    grantPrincipal = "";
    alert($_("admin.granted"));
  } catch (e) {
    alert($_("admin.could_not_grant", { values: { error: e?.message ?? e } }));
  }
}
</script>

<header class="head">
  <h1>{$_('admin.title')}</h1>
  <p>{$_('admin.subtitle')}</p>
</header>

{#if !$isAuthenticated}
  <div class="card warn"><h2>{$_('auth.sign_in_required')}</h2></div>
{:else if loading && !status}
  <div class="state"><Spinner /></div>
{:else if !status?.is_caller_controller}
  <div class="card warn"><h2>{$_('admin.not_controller_h')}</h2><p>{$_('admin.not_controller_body')}</p></div>
{:else}
  <section class="card">
    <h2>{$_('admin.status_h')}</h2>
    <ul class="status">
      <li><strong>{$_('admin.extensions')}</strong> {status.extensions_count}</li>
      <li><strong>{$_('admin.codices')}</strong> {status.codices_count}</li>
      <li><strong>{$_('admin.purchases')}</strong> {status.purchases_count}</li>
      <li><strong>{$_('admin.likes')}</strong> {status.likes_count}</li>
      <li><strong>{$_('admin.licenses')}</strong> {status.licenses_count}</li>
      <li><strong>{$_('admin.file_registry')}</strong> <code>{status.file_registry_canister_id || $_('admin.unset')}</code></li>
      <li><strong>{$_('admin.billing_principal')}</strong> <code>{status.billing_service_principal || $_('admin.unset')}</code></li>
    </ul>
  </section>

  <section class="card">
    <h2>{$_('admin.pending_h', { values: { count: pending.length } })}</h2>
    {#if pending.length === 0}
      <p class="muted">{$_('admin.queue_empty')}</p>
    {:else}
      <table>
        <thead><tr><th>{$_('admin.col_kind')}</th><th>{$_('admin.col_id')}</th><th>{$_('admin.col_name')}</th><th>{$_('admin.col_developer')}</th><th>{$_('admin.col_version')}</th><th>{$_('admin.col_requested')}</th><th></th></tr></thead>
        <tbody>
          {#each pending as p}
            <tr>
              <td>{p.item_kind === 'codex' ? 'codex' : p.item_kind === 'assistant' ? 'assistant' : 'ext'}</td>
              <td><code>{p.item_id}</code></td>
              <td>{p.name}</td>
              <td><code>{shortPrincipal(p.developer)}</code></td>
              <td>{p.version}</td>
              <td>{formatTimeAgo(p.updated_at)}</td>
              <td>
                <button class="btn primary tiny" on:click={() => approve(p)}>{$_('admin.approve')}</button>
                <button class="btn danger tiny" on:click={() => reject(p)}>{$_('admin.reject')}</button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  </section>

  <section class="card">
    <h2>{$_('admin.grant_h')}</h2>
    <p class="muted small">{$_('admin.grant_note')}</p>
    <div class="grid">
      <label>
        <span>{$_('admin.principal')}</span>
        <input type="text" placeholder="abcde-12345-…-cai" bind:value={grantPrincipal} />
      </label>
      <label>
        <span>{$_('admin.days')}</span>
        <input type="number" min="1" bind:value={grantDays} />
      </label>
      <label class="full">
        <span>{$_('admin.note')}</span>
        <input type="text" bind:value={grantNote} />
      </label>
    </div>
    <div class="actions">
      <button class="btn primary" disabled={!grantPrincipal.trim()} on:click={grantLicense}>{$_('admin.grant_btn')}</button>
    </div>
  </section>

  {#if error}<div class="state error">{error}</div>{/if}
{/if}

<style>
  .head h1 { margin: 0 0 0.25rem; font-size: 1.8rem; }
  .head p { margin: 0 0 1.5rem; color: var(--text-muted); }
  .card { background: var(--surface); border: 1px solid var(--border); padding: 1.5rem 1.75rem; border-radius: 0.75rem; margin-bottom: 1.25rem; }
  .card.warn { border-color: var(--border-strong); background: var(--surface-2); color: var(--text); }
  .card h2 { margin: 0 0 0.85rem; font-size: 1.1rem; }
  .status { list-style: none; padding: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.6rem; }
  .status li { background: var(--surface-2); padding: 0.65rem 0.85rem; border-radius: 0.4rem; font-size: 0.85rem; }
  .status code { font-family: monospace; }
  .muted { color: var(--text-faint); }
  .small { font-size: 0.8rem; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 0.55rem; border-bottom: 1px solid var(--surface-2); font-size: 0.85rem; }
  th { color: var(--text-faint); font-weight: 500; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.85rem 1.25rem; margin-top: 0.85rem; }
  .grid label.full { grid-column: 1 / -1; }
  label { display: flex; flex-direction: column; gap: 0.3rem; }
  label span { font-size: 0.8rem; color: var(--text-faint); }
  input { border: 1px solid var(--border); border-radius: 0.4rem; padding: 0.55rem 0.7rem; background: var(--surface); }
  .actions { display: flex; justify-content: flex-end; margin-top: 1rem; }
  .btn { border: 1px solid var(--border); background: var(--surface); color: var(--text-muted); padding: 0.5rem 1rem; border-radius: 0.4rem; }
  .btn:hover:not(:disabled) { background: var(--surface-2); color: var(--text); }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn.primary { background: var(--primary); border-color: var(--primary); color: #fff; }
  .btn.danger { background: var(--danger); border-color: var(--danger); color: #fff; }
  .btn.tiny { padding: 0.3rem 0.6rem; font-size: 0.75rem; margin-right: 0.3rem; }
  .state { text-align: center; padding: 2rem; color: var(--text-muted); }
  .state.error { color: var(--danger); }
</style>
