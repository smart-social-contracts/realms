<script lang="ts">
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { page } from '$app/stores';
  import '../index.scss';

  import { bootstrapAuth, isAuthenticated, login, logout, principalStore } from '$lib/auth';
  import { invalidateActor, marketplace } from '$lib/canisters';
  import { shortPrincipal } from '$lib/format';

  let booted = false;
  let isController = false;

  onMount(async () => {
    if (!browser) return;
    await bootstrapAuth();
    booted = true;
    refreshController();
  });

  async function refreshController() {
    try {
      const r: any = await marketplace.status();
      const status = r?.Ok ?? r;
      isController = Boolean(status?.is_caller_controller);
    } catch {
      isController = false;
    }
  }

  async function handleLogin() {
    await login();
    invalidateActor();
    refreshController();
  }
  async function handleLogout() {
    await logout();
    invalidateActor();
    refreshController();
  }

  $: routeIsActive = (path: string) => {
    if (path === '/') return $page.url.pathname === '/';
    return $page.url.pathname.startsWith(path);
  };
</script>

<header class="topbar">
  <a href="/" class="brand">
    <span class="brand-mark">🛒</span>
    <span class="brand-text">Realms Marketplace</span>
  </a>
  <nav class="nav">
    <a href="/" class:active={routeIsActive('/')}>Top Charts</a>
    <a href="/extensions" class:active={routeIsActive('/extensions')}>Extensions</a>
    <a href="/codices" class:active={routeIsActive('/codices')}>Codices</a>
    <a href="/assistants" class:active={routeIsActive('/assistants')}>Assistants</a>
    <a href="/upload" class:active={routeIsActive('/upload')}>Upload</a>
    <a href="/my-purchases" class:active={routeIsActive('/my-purchases')}>My Purchases</a>
    <a href="/developer" class:active={routeIsActive('/developer')}>Developer</a>
    {#if isController}
      <a href="/admin" class:active={routeIsActive('/admin')}>Admin</a>
    {/if}
  </nav>
  <div class="auth">
    {#if !booted}
      <span class="muted">…</span>
    {:else if $isAuthenticated && $principalStore}
      <span class="who" title={$principalStore.toText()}>{shortPrincipal($principalStore.toText())}</span>
      <button class="btn ghost" on:click={handleLogout}>Sign out</button>
    {:else}
      <button class="btn primary" on:click={handleLogin}>Sign in</button>
    {/if}
  </div>
</header>

<main class="main">
  <slot />
</main>

<footer class="footer">
  <div>
    Realms Marketplace · open source · built on the
    <a href="https://internetcomputer.org" target="_blank" rel="noreferrer">Internet&nbsp;Computer</a>
  </div>
</footer>

<style>
  .topbar {
    position: sticky;
    top: 0;
    z-index: 30;
    display: flex;
    align-items: center;
    gap: 1.25rem;
    padding: 0.85rem 1.5rem;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
  }
  .brand {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    font-weight: 700;
    color: var(--text);
    text-decoration: none;
    font-size: 1.05rem;
  }
  .brand-mark { font-size: 1.4rem; }
  .nav {
    display: flex;
    gap: 0.25rem;
    flex: 1;
    justify-content: center;
    flex-wrap: wrap;
  }
  .nav a {
    padding: 0.5rem 0.85rem;
    border-radius: 0.5rem;
    color: var(--text-muted);
    text-decoration: none;
    font-size: 0.9rem;
    transition: all 0.15s ease;
  }
  .nav a:hover { background: var(--surface-2); color: var(--text); }
  .nav a.active {
    background: var(--primary);
    color: #fff;
  }
  .auth { display: flex; align-items: center; gap: 0.5rem; }
  .who { font-family: monospace; font-size: 0.85rem; color: var(--text-muted); }
  .btn {
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text-muted);
    padding: 0.45rem 0.85rem;
    border-radius: 0.5rem;
    font-size: 0.85rem;
    transition: all 0.15s ease;
  }
  .btn.primary { background: var(--primary); border-color: var(--primary); color: #fff; }
  .btn.primary:hover { background: var(--primary-hover); border-color: var(--primary-hover); }
  .btn.ghost:hover { background: var(--surface-2); color: var(--text); }
  .muted { color: var(--text-faint); }
  .main {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem 1.5rem 4rem;
  }
  .footer {
    padding: 1.5rem;
    border-top: 1px solid var(--border);
    background: var(--surface);
    color: var(--text-faint);
    text-align: center;
    font-size: 0.85rem;
  }
  .footer a { color: var(--text-muted); }

  @media (max-width: 760px) {
    .topbar { flex-direction: column; align-items: stretch; }
    .nav { justify-content: flex-start; overflow-x: auto; }
  }
</style>
