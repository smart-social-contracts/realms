<script lang="ts">import { onMount } from "svelte";
import { browser } from "$app/environment";
import { goto } from "$app/navigation";
import { page } from "$app/stores";
import { _, locale } from "svelte-i18n";
import { initI18n, setLocale, supportedLocales } from "$lib/i18n";
import "../index.scss";
import { bootstrapAuth, isAuthenticated, login, logout, principalStore } from "$lib/auth";
import { invalidateActor, marketplace } from "$lib/canisters";
import { shortPrincipal } from "$lib/format";
let booted = false;
let isController = false;
let searchTerm = "";
let i18nReady = false;
let showLanguageMenu = false;
function submitSearch() {
  const q = searchTerm.trim();
  if (!q) return;
  goto(`/extensions?q=${encodeURIComponent(q)}`);
}
onMount(async () => {
  if (!browser) return;
  await initI18n();
  i18nReady = true;
  await bootstrapAuth();
  booted = true;
  refreshController();
});
$: if (browser && $locale) document.documentElement.lang = $locale;
async function refreshController() {
  try {
    const r = await marketplace.status();
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
$: routeIsActive = (path) => {
  if (path === "/") return $page.url.pathname === "/";
  return $page.url.pathname.startsWith(path);
};
</script>

<svelte:window on:click={() => (showLanguageMenu = false)} />

{#if browser && i18nReady}
<header class="topbar">
  <div class="bar">
    <a href="/" class="brand" aria-label="Realms Marketplace home">
      <img src="/images/logo_horizontal.svg" alt="Realms Marketplace" />
    </a>

    <form class="search" on:submit|preventDefault={submitSearch} role="search">
      <input
        type="search"
        bind:value={searchTerm}
        placeholder={$_('nav.search_placeholder')}
        aria-label={$_('nav.search')}
      />
      <button type="submit" class="icon-btn" aria-label={$_('nav.search')} title={$_('nav.search')}>
        <i class="ti ti-search" aria-hidden="true"></i>
      </button>
    </form>

    <nav class="actions" aria-label="Account and tools">
      {#if isController}
        <a class="icon-btn" href="/admin" class:active={routeIsActive('/admin')} aria-label={$_('nav.admin')} title={$_('nav.admin')}>
          <i class="ti ti-shield-lock" aria-hidden="true"></i>
        </a>
      {/if}

      <div class="lang" on:click|stopPropagation>
        <button
          class="icon-btn"
          on:click={() => (showLanguageMenu = !showLanguageMenu)}
          aria-label={$_('lang.select')}
          title={$_('lang.select')}
          aria-expanded={showLanguageMenu}
        >
          <i class="ti ti-world" aria-hidden="true"></i>
        </button>
        {#if showLanguageMenu}
          <ul class="lang-menu" role="menu">
            {#each supportedLocales as loc}
              <li>
                <button
                  role="menuitemradio"
                  aria-checked={$locale === loc.id}
                  class:active={$locale === loc.id}
                  on:click={() => { setLocale(loc.id); showLanguageMenu = false; }}
                >{loc.name}</button>
              </li>
            {/each}
          </ul>
        {/if}
      </div>

      <span class="divider" aria-hidden="true"></span>

      {#if !booted}
        <span class="muted">…</span>
      {:else if $isAuthenticated && $principalStore}
        <a class="who" href="/my-purchases" title={$principalStore.toText()}>
          <i class="ti ti-user" aria-hidden="true"></i>
          <span class="who-id">{shortPrincipal($principalStore.toText())}</span>
        </a>
        <button class="icon-btn" on:click={handleLogout} aria-label={$_('nav.sign_out')} title={$_('nav.sign_out')}>
          <i class="ti ti-logout" aria-hidden="true"></i>
        </button>
      {:else}
        <button class="icon-btn" on:click={handleLogin} aria-label={$_('nav.sign_in')} title={$_('nav.sign_in')}>
          <i class="ti ti-login" aria-hidden="true"></i>
        </button>
      {/if}
    </nav>
  </div>
</header>

<main class="main">
  <slot />
</main>

<footer class="footer">
  <div class="footer-card">
    <a
      class="social"
      href="https://github.com/smart-social-contracts/realms"
      target="_blank"
      rel="noreferrer"
      aria-label={$_('footer.github')}
      title={$_('footer.github')}
    >
      <i class="ti ti-brand-github" aria-hidden="true"></i>
    </a>
    <div class="build-line">{$_('footer.open_source')}</div>
    <a class="icp" href="https://internetcomputer.org" target="_blank" rel="noreferrer">
      <img src="/images/internet-computer-icp-logo.svg" alt="Internet Computer Logo" width="24" height="24" />
      <span>{$_('footer.built_on_ic')}</span>
    </a>
  </div>
</footer>
{:else}
<div class="loading-screen"><div class="spinner"></div></div>
{/if}

<style>
  .topbar {
    position: sticky;
    top: 0;
    z-index: 30;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
  }
  .bar {
    display: flex;
    align-items: center;
    gap: 1.25rem;
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 1.5rem;
    height: 60px;
  }
  .brand {
    display: inline-flex;
    align-items: center;
    flex-shrink: 0;
    text-decoration: none;
  }
  .brand img {
    height: 30px;
    width: auto;
    display: block;
  }
  .search {
    flex: 1;
    display: flex;
    gap: 0.4rem;
    max-width: 520px;
    margin: 0 auto;
  }
  .search input {
    flex: 1;
    min-width: 0;
    padding: 0.5rem 0.8rem;
    border: 1px solid var(--border);
    border-radius: 0.5rem;
    background: var(--surface-2);
    font-size: 0.9rem;
    color: var(--text);
  }
  .search input:focus {
    outline: none;
    border-color: var(--border-strong);
    background: var(--surface);
  }
  .actions {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    flex-shrink: 0;
  }
  .icon-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 38px;
    height: 38px;
    border: 1px solid transparent;
    background: none;
    color: var(--text-muted);
    border-radius: 0.5rem;
    text-decoration: none;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .icon-btn .ti { font-size: 1.25rem; line-height: 1; }
  .icon-btn:hover { background: var(--surface-2); color: var(--text); }
  .icon-btn.active { background: var(--surface-3); color: var(--text); }
  .search .icon-btn { border-color: var(--border); }
  .divider {
    width: 1px;
    height: 24px;
    background: var(--border);
    margin: 0 0.25rem;
  }
  .who {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.85rem;
    color: var(--text-muted);
    white-space: nowrap;
    text-decoration: none;
    padding: 0.35rem 0.5rem;
    border-radius: 0.5rem;
    transition: all 0.12s ease;
  }
  .who:hover { background: var(--surface-2); color: var(--text); }
  .who .ti { font-size: 1.1rem; }
  .who-id { font-family: 'SF Mono', 'Fira Code', monospace; }
  .muted { color: var(--text-faint); }

  .lang { position: relative; display: inline-flex; }
  .lang-menu {
    position: absolute;
    top: calc(100% + 6px);
    right: 0;
    min-width: 160px;
    margin: 0;
    padding: 0.35rem;
    list-style: none;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 0.6rem;
    box-shadow: 0 10px 30px -12px rgba(0, 0, 0, 0.25);
    z-index: 60;
  }
  .lang-menu li { margin: 0; }
  .lang-menu button {
    display: block;
    width: 100%;
    text-align: left;
    padding: 0.5rem 0.7rem;
    border: none;
    background: none;
    border-radius: 0.4rem;
    color: var(--text-muted);
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.12s ease;
  }
  .lang-menu button:hover { background: var(--surface-2); color: var(--text); }
  .lang-menu button.active { color: var(--text); font-weight: 600; background: var(--surface-3); }

  .loading-screen {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
  }
  .spinner {
    width: 32px;
    height: 32px;
    border: 3px solid var(--surface-2);
    border-top-color: var(--primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .main {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem 1.5rem 4rem;
  }

  /* Footer mirrors the realm_frontend footer: a centered card with a
     GitHub link, a muted text line, and the "Built on the Internet
     Computer" badge. */
  .footer {
    padding: 0 1.5rem 1.5rem;
  }
  .footer-card {
    max-width: 1200px;
    margin: 0 auto;
    padding: 1.5rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 0.75rem;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
  }
  .footer-card .social {
    color: var(--text-muted);
    text-decoration: none;
    transition: color 0.15s ease;
  }
  .footer-card .social:hover { color: var(--text); }
  .footer-card .social .ti { font-size: 1.4rem; }
  .footer-card .build-line {
    font-size: 0.75rem;
    color: var(--text-faint);
  }
  .footer-card .icp {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    color: var(--text-muted);
    text-decoration: none;
    font-size: 0.875rem;
    transition: color 0.15s ease;
  }
  .footer-card .icp:hover { color: var(--text); }
  .footer-card .icp img { width: 24px; height: 24px; display: block; }

  @media (max-width: 760px) {
    .bar {
      flex-wrap: wrap;
      height: auto;
      padding-top: 0.7rem;
      padding-bottom: 0.7rem;
      gap: 0.6rem;
    }
    .brand { order: 1; }
    .actions { order: 2; margin-left: auto; }
    .search { order: 3; flex-basis: 100%; max-width: none; margin: 0; }
  }
</style>
