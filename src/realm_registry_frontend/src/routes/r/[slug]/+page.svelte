<script>
  import { onMount, onDestroy } from 'svelte';
  import { browser } from '$app/environment';
  import { page } from '$app/stores';
  import { resolveSlug } from '$lib/slug-resolver.js';
  import { realmIframeUrl, portalPath } from '$lib/federation.js';
  import { attachPortalBridge } from '$lib/portal-bridge-host.js';
  import { CONFIG } from '$lib/config.js';

  let iframeEl;
  let loading = true;
  let error = '';
  let realm = null;
  let bridge = null;

  $: slug = $page.params.slug;
  $: subPath = $page.url.pathname.replace(new RegExp(`^/r/${slug}`), '') || '/';

  onMount(async () => {
    if (!browser) return;
    await loadRealm();
  });

  onDestroy(() => {
    bridge?.dispose?.();
  });

  async function loadRealm() {
    loading = true;
    error = '';
    bridge?.dispose?.();
    bridge = null;
    try {
      const data = await resolveSlug(slug);
      realm = {
        slug: data.slug,
        backendCanisterId: data.backend_canister_id,
        frontendCanisterId: data.frontend_canister_id,
        portalUrl: data.portal_url,
        loaderProfile: data.loader_profile || 'realms-iframe-v1',
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
    bridge?.dispose?.();
    bridge = attachPortalBridge(iframeEl, realm);
    const path = subPath === '/' ? '/join' : subPath;
    bridge.syncPath(path);
  }

  $: iframePath = subPath === '/' ? '/join' : subPath;

  $: iframeSrc =
    realm && browser
      ? realmIframeUrl(realm.frontendCanisterId, realm.slug, iframePath)
      : '';
</script>

<svelte:head>
  <title>{slug} — Realms</title>
</svelte:head>

<div class="portal-shell">
  <header class="portal-bar">
    <a href="/" class="home-link">← Registry</a>
    <span class="slug">/r/{slug}</span>
    {#if realm}
      <span class="canister-id" title="Realm frontend canister (not your II principal)">{realm.frontendCanisterId}</span>
    {/if}
  </header>

  {#if loading}
    <p class="status">Resolving realm…</p>
  {:else if error}
    <div class="error-box">
      <p>{error}</p>
      <a href="/">Back to registry</a>
    </div>
  {:else if realm}
    <iframe
      bind:this={iframeEl}
      title="Realm {slug}"
      src={iframeSrc}
      sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
      referrerpolicy="no-referrer"
      on:load={onIframeLoad}
      class="realm-frame"
    ></iframe>
  {/if}
</div>

<style>
  .portal-shell {
    display: flex;
    flex-direction: column;
    min-height: calc(100vh - 4rem);
  }
  .portal-bar {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.5rem 1rem;
    font-size: 0.875rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    flex-wrap: wrap;
  }
  .home-link {
    color: #93c5fd;
    text-decoration: none;
  }
  .slug {
    font-weight: 600;
  }
  .canister-id {
    opacity: 0.65;
    font-family: monospace;
    font-size: 0.75rem;
    margin-left: auto;
  }
  .realm-frame {
    flex: 1;
    width: 100%;
    min-height: 70vh;
    border: none;
    background: #111;
  }
  .status,
  .error-box {
    padding: 2rem;
    text-align: center;
  }
  .error-box {
    color: #f87171;
  }
</style>
