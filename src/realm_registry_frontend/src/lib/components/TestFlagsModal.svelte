<script>
  import { backend } from '$lib/canisters.js';
  import {
    registryRuntimeFlags,
    getRegistryRuntimeFlagsSnapshot
  } from '$lib/stores/registryRuntimeFlags.js';

  export let open = false;

  const FLAGS = [
    { key: 'test_mode', store: 'testMode', label: 'Test mode', hint: 'Master switch — turning this off hides this editor and locks flags to controllers' },
    { key: 'ii_bypass', store: 'testModeIIBypass', label: 'II bypass', hint: 'Skip Internet Identity and sign in with deterministic test identities' },
    { key: 'user_self_registration', store: 'testModeUserSelfRegistration', label: 'User self-registration', hint: 'Allow users to join without an invitation code' },
    { key: 'demo_data', store: 'testModeDemoData', label: 'Demo data', hint: 'Auto-activate the demo data simulator' },
    { key: 'skip_terms', store: 'testModeSkipTerms', label: 'Skip terms', hint: 'Skip the terms & conditions step on join' },
    { key: 'skip_passport_zkproof', store: 'testModeSkipPassportZkproof', label: 'Skip passport ZK-proof', hint: 'Bypass passport zero-knowledge verification' }
  ];

  let values = {};
  let saving = false;
  let error = '';
  let message = '';

  $: if (open) syncFromStore();

  function syncFromStore() {
    const snapshot = getRegistryRuntimeFlagsSnapshot();
    const next = {};
    for (const f of FLAGS) next[f.key] = !!snapshot[f.store];
    values = next;
    error = '';
    message = '';
  }

  function close() {
    if (saving) return;
    open = false;
  }

  async function save() {
    saving = true;
    error = '';
    message = '';
    try {
      const raw = await backend.set_test_flags_json(JSON.stringify({ test_flags: values }));
      const result = typeof raw === 'string' ? JSON.parse(raw) : raw;
      if (!result?.success) {
        throw new Error(result?.error || 'Failed to update test flags');
      }
      await registryRuntimeFlags.fetch();
      message = 'Test flags updated';
      if (!values.test_mode) open = false;
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      saving = false;
    }
  }

  function handleWindowKeydown(event) {
    if (!open || saving) return;
    if (event.key === 'Escape') close();
  }
</script>

<svelte:window on:keydown={handleWindowKeydown} />

{#if open}
  <div class="overlay-wrap">
    <button type="button" class="backdrop" aria-label="Close" on:click={close}></button>
    <div
      class="dialog"
      role="dialog"
      aria-modal="true"
      tabindex="-1"
      aria-labelledby="test-flags-modal-title"
    >
      <h2 id="test-flags-modal-title" class="title">Test flags</h2>
      <p class="subtitle">
        This registry runs in test mode. Anyone can view and change these runtime flags while
        test mode is enabled.
      </p>

      <div class="flags">
        {#each FLAGS as flag}
          <label class="flag-row">
            <span class="flag-text">
              <span class="flag-label">{flag.label}</span>
              <span class="flag-hint">{flag.hint}</span>
            </span>
            <input type="checkbox" bind:checked={values[flag.key]} disabled={saving} />
          </label>
        {/each}
      </div>

      {#if error}
        <p class="feedback error">{error}</p>
      {/if}
      {#if message}
        <p class="feedback success">{message}</p>
      {/if}

      <div class="actions">
        <button type="button" class="btn btn-cancel" disabled={saving} on:click={close}>
          Close
        </button>
        <button type="button" class="btn btn-confirm" disabled={saving} on:click={save}>
          {saving ? 'Saving…' : 'Save'}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .overlay-wrap {
    position: fixed;
    inset: 0;
    z-index: 2000;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem;
  }

  .backdrop {
    position: absolute;
    inset: 0;
    border: none;
    padding: 0;
    margin: 0;
    background: rgba(0, 0, 0, 0.45);
    backdrop-filter: blur(2px);
    cursor: default;
  }

  .dialog {
    position: relative;
    z-index: 1;
    width: 100%;
    max-width: 460px;
    background: #fff;
    border-radius: 0.875rem;
    padding: 1.5rem;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  }

  .title {
    margin: 0 0 0.25rem;
    font-size: 1.125rem;
    font-weight: 700;
    color: #171717;
  }

  .subtitle {
    margin: 0 0 1rem;
    font-size: 0.8125rem;
    line-height: 1.45;
    color: #737373;
  }

  .flags {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }

  .flag-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 1rem;
    cursor: pointer;
  }

  .flag-text {
    display: flex;
    flex-direction: column;
    gap: 0.125rem;
  }

  .flag-label {
    font-size: 0.875rem;
    font-weight: 600;
    color: #171717;
  }

  .flag-hint {
    font-size: 0.75rem;
    line-height: 1.4;
    color: #737373;
  }

  .flag-row input[type='checkbox'] {
    margin-top: 0.2rem;
    width: 1.05rem;
    height: 1.05rem;
    accent-color: #171717;
    flex-shrink: 0;
  }

  .feedback {
    margin: 0 0 0.75rem;
    font-size: 0.8125rem;
  }

  .feedback.error {
    color: #b91c1c;
  }

  .feedback.success {
    color: #15803d;
  }

  .actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.5rem;
  }

  .btn {
    padding: 0.5rem 1rem;
    border-radius: 0.5rem;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    border: 1px solid transparent;
  }

  .btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .btn-cancel {
    background: #fff;
    color: #171717;
    border-color: #d4d4d4;
  }

  .btn-cancel:hover:not(:disabled) {
    background: #fafafa;
  }

  .btn-confirm {
    background: #171717;
    color: #fff;
  }

  .btn-confirm:hover:not(:disabled) {
    filter: brightness(1.05);
  }
</style>
