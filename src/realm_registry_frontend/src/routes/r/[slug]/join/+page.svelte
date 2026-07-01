<script>
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { page } from '$app/stores';
  import { resolveSlug } from '$lib/slug-resolver.js';
  import { realmIframeUrl } from '$lib/federation.js';
  import { attachPortalBridge } from '$lib/portal-bridge-host.js';
  import { CONFIG } from '$lib/config.js';

  let iframeEl;
  let loading = true;
  let error = '';
  let realm = null;
  let bridge = null;

  $: slug = $page.params.slug;

  onMount(async () => {
    if (!browser) return;
    await loadRealm();
  });

  async function loadRealm() {
    loading = true;
    error = '';
    try {
      const data = await resolveSlug(slug);
      realm = {
        slug: data.slug,
        backendCanisterId: data.backend_canister_id,
        frontendCanisterId: data.frontend_canister_id,
        env: CONFIG.deploy_queue_network
      };
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  }

  function onIframeLoad() {
    if (!iframeEl || !realm) return;
    bridge = attachPortalBridge(iframeEl, realm);
    bridge.syncPath('/join');
  }

  $: iframeSrc = realm && browser ? realmIframeUrl(realm.frontendCanisterId, realm.slug, '/join') : '';
</script>

<svelte:head>
  <title>Join {slug} — Realms</title>
</svelte:head>

<div class="join-shell">
  {#if loading}
    <p>Loading join flow…</p>
  {:else if error}
    <p class="error">{error}</p>
  {:else if realm}
    <iframe
      bind:this={iframeEl}
      title="Join {slug}"
      src={iframeSrc}
      sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
      referrerpolicy="no-referrer"
      on:load={onIframeLoad}
      class="realm-frame"
    ></iframe>
  {/if}
</div>

<style>
  .join-shell {
    min-height: 70vh;
  }
  .realm-frame {
    width: 100%;
    min-height: 70vh;
    border: none;
  }
  .error {
    color: #f87171;
    padding: 2rem;
  }
</style>
