<script>
  import { onMount } from 'svelte';
  import { backend } from '$lib/canisters';

  let packages = [];
  let loading = true;
  let error = null;
  let busy = false;

  function parseResult(raw) {
    if (raw == null) return null;
    if (typeof raw === 'string') {
      try {
        return JSON.parse(raw);
      } catch (e) {
        return { success: false, error: raw };
      }
    }
    return raw;
  }

  async function loadPackages() {
    loading = true;
    error = null;
    try {
      const raw = await backend.list_packages();
      const data = parseResult(raw);
      if (!data || data.success === false) {
        error = (data && data.error) || 'Could not load packages';
        packages = [];
      } else {
        packages = data.packages || [];
      }
    } catch (e) {
      error = e?.message || String(e);
      packages = [];
    } finally {
      loading = false;
    }
  }

  async function runAction(method, payload) {
    if (busy) return;
    busy = true;
    error = null;
    try {
      const raw = await backend[method](JSON.stringify(payload));
      const data = parseResult(raw);
      if (!data || data.success === false) {
        error = (data && data.error) || `${method} failed`;
      }
      await loadPackages();
    } catch (e) {
      error = e?.message || String(e);
    } finally {
      busy = false;
    }
  }

  function lockRow(row) {
    return runAction('lock_package', { id: row.id });
  }

  function unlockRow(row) {
    return runAction('unlock_package', { id: row.id });
  }

  function transferRow(row) {
    const owner = window.prompt(
      `Transfer '${row.id}' to principal or department:`,
      row.owner || ''
    );
    if (owner == null) return;
    const trimmed = String(owner).trim();
    if (!trimmed) return;
    return runAction('transfer_package', { id: row.id, owner: trimmed });
  }

  onMount(loadPackages);
</script>

<div class="mb-8">
  <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-4">
    <div>
      <h3 class="text-xl font-bold text-gray-900 mb-1">Package Manager</h3>
      <p class="text-sm text-gray-600 max-w-2xl">
        Installed Codex and extensions. Re-install replaces leftover stems.
        Locked packages can only be replaced by the owner (or root / Congress /
        <code class="text-xs">codex.revert</code>).
      </p>
    </div>
    <button
      class="text-sm text-gray-700 underline disabled:opacity-50"
      on:click={loadPackages}
      disabled={busy}
    >
      Refresh
    </button>
  </div>

  {#if loading}
    <p class="text-sm text-gray-600">Loading packages…</p>
  {:else if packages.length === 0}
    <p class="text-sm text-gray-600">No installed packages recorded.</p>
  {:else}
    <div class="overflow-x-auto border rounded-lg">
      <table class="min-w-full text-sm">
        <thead class="bg-gray-50 text-left text-gray-600">
          <tr>
            <th class="px-3 py-2 font-medium">id</th>
            <th class="px-3 py-2 font-medium">version</th>
            <th class="px-3 py-2 font-medium">owner</th>
            <th class="px-3 py-2 font-medium">lock</th>
            <th class="px-3 py-2 font-medium">actions</th>
          </tr>
        </thead>
        <tbody>
          {#each packages as row}
            <tr class="border-t">
              <td class="px-3 py-2 font-medium text-gray-900 break-all">
                {row.id}
                {#if row.kind}
                  <span class="ml-1 text-xs text-gray-500">{row.kind}</span>
                {/if}
              </td>
              <td class="px-3 py-2 text-gray-800">{row.version || '—'}</td>
              <td class="px-3 py-2 text-gray-800 break-all">{row.owner || '—'}</td>
              <td class="px-3 py-2">{row.locked ? 'locked' : 'unlocked'}</td>
              <td class="px-3 py-2">
                <div class="flex flex-wrap gap-2">
                  {#if row.locked}
                    <button
                      class="text-xs underline disabled:opacity-50"
                      on:click={() => unlockRow(row)}
                      disabled={busy}
                    >
                      Unlock
                    </button>
                  {:else}
                    <button
                      class="text-xs underline disabled:opacity-50"
                      on:click={() => lockRow(row)}
                      disabled={busy}
                    >
                      Lock
                    </button>
                  {/if}
                  <button
                    class="text-xs underline disabled:opacity-50"
                    on:click={() => transferRow(row)}
                    disabled={busy}
                  >
                    Transfer
                  </button>
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}

  {#if error}
    <p class="mt-3 text-sm text-red-700">{error}</p>
  {/if}
</div>
