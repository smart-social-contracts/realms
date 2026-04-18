<script lang="ts">
  import { goto } from '$app/navigation';
  import Spinner from '$lib/components/Spinner.svelte';
  import { isAuthenticated, principalStore } from '$lib/auth';
  import { uploadAndPublish, type UploadFolderItem, type UploadProgress } from '$lib/file-registry-client';
  import { marketplaceClient } from '$lib/marketplace-client';

  type Kind = 'ext' | 'codex';

  let step: 1 | 2 | 3 | 4 = 1;
  let kind: Kind = 'ext';

  // Step 1 — metadata
  let id = '';
  let realmType = '';
  let name = '';
  let description = '';
  let version = '0.1.0';
  let priceUsdCents = 0;     // display-only, stored as e8s
  let icon = '';
  let categoriesStr = 'other';

  // Step 2 — files
  let pickedFiles: File[] = [];
  let baseFolder = '';

  // Step 3 — uploading
  let registryCanisterId = '';
  let registryError = '';
  let uploadProgress: Record<string, UploadProgress> = {};
  let uploading = false;
  let uploadError = '';

  // Step 4 — done
  let listingHref = '';

  $: if (kind === 'ext' && id.includes('/')) id = id.replace(/\//g, '_');

  // <input webkitdirectory> isn't in the standard HTML typings; pass via spread.
  const dirInputAttrs: Record<string, string> = { webkitdirectory: '', directory: '' };
  $: ns = (() => {
    if (!id || !version) return '';
    if (kind === 'ext') return `ext/${id}/${version}`;
    return `codex/${id}/${version}`;
  })();

  async function loadRegistry() {
    try {
      registryCanisterId = await marketplaceClient.getFileRegistryCanisterId();
      if (!registryCanisterId) registryError = 'Marketplace has no file_registry configured (controller must call set_file_registry_canister_id).';
    } catch (e: any) {
      registryError = e?.message ?? String(e);
    }
  }

  function onFiles(e: Event) {
    const input = e.target as HTMLInputElement;
    const list: File[] = Array.from(input.files ?? []);
    pickedFiles = list;
    if (list.length > 0) {
      // webkitdirectory paths look like "<folder>/sub/file.ext"
      const first = (list[0] as any).webkitRelativePath as string;
      baseFolder = first?.split('/')?.[0] ?? '';
    }
  }

  function relativePath(f: File): string {
    const wkrel = (f as any).webkitRelativePath as string | undefined;
    if (wkrel) {
      // strip the top-level folder so we don't end up with "myext/manifest.json".
      const parts = wkrel.split('/');
      if (parts.length > 1) return parts.slice(1).join('/');
      return wkrel;
    }
    return f.name;
  }

  function totalBytes(): number {
    return pickedFiles.reduce((s, f) => s + f.size, 0);
  }

  async function startUpload() {
    if (!ns || pickedFiles.length === 0) return;
    if (!registryCanisterId) await loadRegistry();
    if (!registryCanisterId) {
      uploadError = registryError || 'No file_registry available';
      return;
    }
    uploading = true;
    uploadError = '';
    uploadProgress = {};
    step = 3;

    const items: UploadFolderItem[] = pickedFiles.map((f) => ({ path: relativePath(f), file: f }));
    try {
      await uploadAndPublish(registryCanisterId, ns, items, (p) => {
        uploadProgress = { ...uploadProgress, [p.path]: p };
      });

      // Register listing on marketplace_backend
      const priceE8s = BigInt(Math.max(0, Math.round(priceUsdCents / 100 * 100_000_000))); // approximation: $1 ≈ 1 ICP for display
      if (kind === 'ext') {
        await marketplaceClient.createExtension({
          extension_id: id,
          name,
          description,
          version,
          price_e8s: priceE8s,
          icon,
          categories: categoriesStr,
          file_registry_canister_id: registryCanisterId,
          file_registry_namespace: ns,
          download_url: '',
        });
        listingHref = `/extensions/${encodeURIComponent(id)}`;
      } else {
        await marketplaceClient.createCodex({
          codex_id: id,
          realm_type: realmType,
          name,
          description,
          version,
          price_e8s: priceE8s,
          icon,
          categories: categoriesStr,
          file_registry_canister_id: registryCanisterId,
          file_registry_namespace: ns,
        });
        listingHref = `/codices/${encodeURIComponent(id)}`;
      }
      step = 4;
    } catch (e: any) {
      uploadError = e?.message ?? String(e);
    } finally {
      uploading = false;
    }
  }

  function reset() {
    step = 1;
    pickedFiles = [];
    uploadProgress = {};
    uploadError = '';
    listingHref = '';
  }
</script>

<header class="head">
  <h1>Upload</h1>
  <p>Publish an extension or codex. Files go to the file_registry canister; the marketplace stores the metadata and a pointer.</p>
</header>

{#if !$isAuthenticated}
  <div class="card warn">
    <h2>Sign in required</h2>
    <p>You need to sign in with Internet Identity before you can upload.</p>
    <p>(Anyone can upload — a developer license is only required to request an audit.)</p>
  </div>
{:else}
  <div class="wizard">
    <ol class="steps">
      <li class:active={step === 1} class:done={step > 1}>1. Type &amp; metadata</li>
      <li class:active={step === 2} class:done={step > 2}>2. Pick files</li>
      <li class:active={step === 3} class:done={step > 3}>3. Upload</li>
      <li class:active={step === 4}>4. Done</li>
    </ol>

    {#if step === 1}
      <section class="card">
        <h2>What are you uploading?</h2>
        <div class="kind-switch">
          <button class:active={kind === 'ext'} on:click={() => (kind = 'ext')}>🧩 Extension</button>
          <button class:active={kind === 'codex'} on:click={() => (kind = 'codex')}>📜 Codex</button>
        </div>

        <div class="grid">
          <label>
            <span>{kind === 'ext' ? 'extension_id' : 'codex_id'}</span>
            <input type="text" placeholder={kind === 'ext' ? 'voting' : 'syntropia/membership'} bind:value={id} />
          </label>
          {#if kind === 'codex'}
            <label>
              <span>realm_type (optional)</span>
              <input type="text" placeholder="syntropia" bind:value={realmType} />
            </label>
          {/if}
          <label>
            <span>version</span>
            <input type="text" placeholder="0.1.0" bind:value={version} />
          </label>
          <label>
            <span>name</span>
            <input type="text" placeholder="Token-weighted Voting" bind:value={name} />
          </label>
          <label class="full">
            <span>description</span>
            <textarea rows="3" bind:value={description} />
          </label>
          <label>
            <span>icon (emoji or short name)</span>
            <input type="text" placeholder="🗳️" bind:value={icon} />
          </label>
          <label>
            <span>categories (comma-separated)</span>
            <input type="text" placeholder="public_services,governance" bind:value={categoriesStr} />
          </label>
          <label>
            <span>price (USD cents — display only, no on-chain transfer)</span>
            <input type="number" min="0" step="50" bind:value={priceUsdCents} />
          </label>
        </div>

        <p class="namespace-preview">
          file_registry namespace: <code>{ns || '(set id and version)'}</code>
        </p>

        <div class="actions">
          <button class="btn primary" disabled={!id || !name || !version} on:click={() => (step = 2)}>Next →</button>
        </div>
      </section>
    {:else if step === 2}
      <section class="card">
        <h2>Pick the files to publish</h2>
        <p class="muted">
          Choose a folder. For extensions we expect <code>manifest.json</code>, <code>backend/…</code>, <code>frontend/dist/index.js</code>.
          For codices, flat <code>*.py</code> files.
        </p>
        <input
          type="file"
          multiple
          {...dirInputAttrs}
          on:change={onFiles}
        />

        {#if pickedFiles.length > 0}
          <table class="files">
            <thead><tr><th>Path in namespace</th><th>Size</th></tr></thead>
            <tbody>
              {#each pickedFiles as f}
                <tr>
                  <td><code>{relativePath(f)}</code></td>
                  <td>{(f.size / 1024).toFixed(1)} KB</td>
                </tr>
              {/each}
            </tbody>
          </table>
          <p class="muted">{pickedFiles.length} files · {(totalBytes() / 1024 / 1024).toFixed(2)} MB</p>
        {/if}

        <div class="actions">
          <button class="btn ghost" on:click={() => (step = 1)}>← Back</button>
          <button class="btn primary" disabled={pickedFiles.length === 0} on:click={startUpload}>
            Upload &amp; publish
          </button>
        </div>
      </section>
    {:else if step === 3}
      <section class="card">
        <h2>Uploading…</h2>
        <p class="muted">Direct browser → file_registry. Each file uploads in 128 KB chunks.</p>
        {#if uploadError}
          <p class="error">⚠️ {uploadError}</p>
          <div class="actions">
            <button class="btn" on:click={() => (step = 2)}>Back</button>
            <button class="btn primary" on:click={startUpload}>Retry</button>
          </div>
        {:else}
          <div class="progress-list">
            {#each pickedFiles as f}
              {#if uploadProgress[relativePath(f)]}
                {@const p = uploadProgress[relativePath(f)]}
                <div class="row">
                  <div class="path"><code>{p.path}</code></div>
                  <div class="bar">
                    <div class="fill" style="width: {Math.min(100, (p.uploaded / Math.max(1, p.total)) * 100)}%"></div>
                  </div>
                  <div class="status">{p.status}</div>
                </div>
              {:else}
                <div class="row pending">
                  <div class="path"><code>{relativePath(f)}</code></div>
                  <div class="bar"></div>
                  <div class="status">queued</div>
                </div>
              {/if}
            {/each}
          </div>
          {#if uploading}
            <div class="centered"><Spinner /></div>
          {/if}
        {/if}
      </section>
    {:else if step === 4}
      <section class="card success">
        <h2>✅ Published!</h2>
        <p>Your {kind === 'ext' ? 'extension' : 'codex'} is live. Files served from the file_registry canister.</p>
        <div class="actions">
          <a class="btn primary" href={listingHref}>View listing →</a>
          <button class="btn ghost" on:click={reset}>Upload another</button>
        </div>
      </section>
    {/if}
  </div>
{/if}

<style>
  .head h1 { margin: 0 0 0.25rem; font-size: 1.8rem; }
  .head p { margin: 0 0 1.5rem; color: var(--text-muted); }
  .wizard { max-width: 760px; margin: 0 auto; }
  .steps {
    list-style: none; display: flex; gap: 1rem; padding: 0; margin: 0 0 1.5rem;
    flex-wrap: wrap;
  }
  .steps li {
    flex: 1; min-width: 130px;
    padding: 0.6rem 0.85rem; border: 1px solid var(--border);
    border-radius: 0.5rem; background: var(--surface);
    color: var(--text-faint); font-size: 0.85rem;
  }
  .steps li.active { border-color: var(--primary); color: var(--text); font-weight: 600; }
  .steps li.done { border-color: var(--success); color: var(--success); }
  .card {
    background: var(--surface); border: 1px solid var(--border);
    padding: 1.5rem 1.75rem; border-radius: 0.75rem;
  }
  .card.success { border-color: var(--success); background: var(--verified-bg); color: var(--verified); }
  .card.warn { border-color: var(--warning); background: #FEF3C7; color: #92400E; }
  .card h2 { margin: 0 0 0.5rem; font-size: 1.15rem; }
  .kind-switch { display: flex; gap: 0.5rem; margin: 1rem 0 1.25rem; }
  .kind-switch button {
    background: var(--surface-2); border: 1px solid var(--border);
    padding: 0.6rem 1rem; border-radius: 0.5rem;
    color: var(--text-muted);
  }
  .kind-switch button.active {
    background: var(--primary); border-color: var(--primary); color: #fff;
  }
  .grid {
    display: grid; grid-template-columns: 1fr 1fr; gap: 0.85rem 1.25rem;
  }
  .grid label.full { grid-column: 1 / -1; }
  label { display: flex; flex-direction: column; gap: 0.3rem; }
  label span { font-size: 0.8rem; color: var(--text-faint); }
  input, textarea {
    border: 1px solid var(--border); border-radius: 0.4rem;
    padding: 0.55rem 0.7rem; background: var(--surface); font: inherit; color: var(--text);
  }
  input:focus, textarea:focus { outline: 2px solid var(--accent); outline-offset: -1px; }
  .namespace-preview { color: var(--text-muted); margin-top: 1rem; font-size: 0.85rem; }
  .namespace-preview code { background: var(--surface-2); padding: 0.15rem 0.45rem; border-radius: 0.3rem; }
  .actions { display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 1.5rem; }
  .btn {
    border: 1px solid var(--border); background: var(--surface); color: var(--text-muted);
    padding: 0.5rem 1rem; border-radius: 0.5rem; text-decoration: none;
  }
  .btn:hover:not(:disabled) { background: var(--surface-2); color: var(--text); }
  .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn.primary { background: var(--primary); border-color: var(--primary); color: #fff; }
  .btn.primary:hover:not(:disabled) { background: var(--primary-hover); }
  .btn.ghost { background: transparent; }
  .files { width: 100%; border-collapse: collapse; margin: 1rem 0 0.5rem; }
  .files th, .files td { text-align: left; padding: 0.4rem 0.5rem; border-bottom: 1px solid var(--surface-2); font-size: 0.85rem; }
  .files th { color: var(--text-faint); font-weight: 500; }
  .progress-list { display: flex; flex-direction: column; gap: 0.5rem; margin: 1.25rem 0; }
  .progress-list .row { display: grid; grid-template-columns: 1fr 200px 90px; gap: 1rem; align-items: center; }
  .path code { font-size: 0.85rem; }
  .bar {
    background: var(--surface-2); height: 8px; border-radius: 999px; overflow: hidden;
  }
  .fill { background: var(--success); height: 100%; transition: width 0.2s ease; }
  .status { text-transform: capitalize; font-size: 0.8rem; color: var(--text-muted); }
  .centered { text-align: center; padding: 1rem 0; }
  .error { color: var(--danger); }
  .muted { color: var(--text-muted); font-size: 0.85rem; }
</style>
