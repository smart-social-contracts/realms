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
import { resolveCasalsUrl } from "$lib/config";

$: casalsUrl = browser ? resolveCasalsUrl() : "";
$: isHome = $page.url.pathname === "/";
let booted = false;
let isController = false;
let searchTerm = "";
let i18nReady = false;
let showLanguageMenu = false;
let heroScrolled = false;
function submitSearch() {
  const q = searchTerm.trim();
  if (!q) return;
  goto(`/?q=${encodeURIComponent(q)}`);
}
function onWindowScroll() {
  heroScrolled = window.scrollY > 24;
}
onMount(async () => {
  if (!browser) return;
  await initI18n();
  i18nReady = true;
  await bootstrapAuth();
  booted = true;
  refreshController();
  onWindowScroll();
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

<svelte:window on:click={() => (showLanguageMenu = false)} on:scroll={onWindowScroll} />

{#if browser && i18nReady}
{#if isHome}
  <div class="hero-chrome" class:hidden={heroScrolled}>
    {#if $isAuthenticated && $principalStore}
      <a class="hero-chrome-btn" href="/my-purchases" aria-label={$_('nav.my_purchases')} title={$principalStore.toText()}>
        <i class="ti ti-user" aria-hidden="true"></i>
        <span class="hero-chrome-label">{shortPrincipal($principalStore.toText())}</span>
      </a>
    {:else}
      <button class="hero-chrome-btn" on:click={handleLogin} aria-label={$_('nav.sign_in')} title={$_('nav.sign_in')}>
        <i class="ti ti-login" aria-hidden="true"></i>
        <span class="hero-chrome-label">{$_('nav.sign_in')}</span>
      </button>
    {/if}
  </div>
{/if}
<header class="topbar" class:overlay={isHome} class:revealed={!isHome || heroScrolled}>
  <div class="bar">
    <div class="brand-group">
      <a href="/" class="brand" aria-label="Realms Marketplace home">
        <img src="/images/logo_horizontal.svg" alt="Realms Marketplace" />
      </a>
      <a href="/about" class="chrome-link" class:active={routeIsActive('/about')}>{$_('nav.about')}</a>
    </div>

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

<main class="main" class:flush={$page.url.pathname === '/'}>
  <slot />
</main>

<footer class="footer">
  <div class="footer-card">
    <div class="socials">
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
      {#if casalsUrl}
        <a
          class="social casals"
          href={casalsUrl}
          target="_blank"
          rel="noreferrer"
          aria-label={$_('footer.casals')}
          title={$_('footer.casals')}
        >
          <img src="/images/casals-logo.png" alt="" width="28" height="28" />
        </a>
      {/if}
    </div>
    <div class="build-line">{$_('footer.open_source')}</div>
    <div class="build-meta">{$_('footer.build', { values: { version: __BUILD_VERSION__, commit: __BUILD_COMMIT__ } })}</div>
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
  .topbar.overlay {
    position: fixed;
    left: 0;
    right: 0;
    top: 0;
    transition: transform 0.25s ease, opacity 0.2s ease, visibility 0.2s;
  }
  .topbar.overlay:not(.revealed) {
    transform: translateY(-100%);
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
  }
  .topbar.overlay.revealed,
  .topbar.overlay:focus-within {
    transform: none;
    opacity: 1;
    visibility: visible;
    pointer-events: auto;
  }
  .hero-chrome {
    position: fixed;
    z-index: 31;
    top: 1.15rem;
    right: 1.5rem;
    display: flex;
    gap: 0.4rem;
    transition: opacity 0.2s ease, visibility 0.2s;
  }
  .hero-chrome.hidden {
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
  }
  .hero-chrome-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.4rem;
    height: 2.4rem;
    padding: 0 0.9rem 0 0.7rem;
    border: 1px solid var(--border);
    border-radius: 999px;
    background: #ffffffdb;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    color: var(--text);
    font-size: 0.875rem;
    font-weight: 600;
    text-decoration: none;
    cursor: pointer;
    box-shadow: 0 1px 2px #0000000a;
    transition: background 0.15s ease, border-color 0.15s ease;
  }
  .hero-chrome-btn .ti { font-size: 1.15rem; line-height: 1; }
  .hero-chrome-btn:hover { background: var(--surface); border-color: var(--border-strong); }
  .bar {
    display: flex;
    align-items: center;
    gap: 1.25rem;
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 1.5rem;
    height: 60px;
  }
  .brand-group {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    flex-shrink: 0;
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
  .chrome-link {
    flex-shrink: 0;
    font-size: 0.9rem;
    font-weight: 600;
    color: var(--text-muted);
    text-decoration: none;
    padding: 0.35rem 0.55rem;
    border-radius: 0.45rem;
    transition: color 0.15s ease, background 0.15s ease;
  }
  .chrome-link:hover { color: var(--text); background: var(--surface-2); }
  .chrome-link.active { color: var(--text); }
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
  .main.flush {
    max-width: none;
    padding: 0 0 4rem;
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
  .footer-card .socials {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
  }
  .footer-card .social {
    color: var(--text-muted);
    text-decoration: none;
    transition: color 0.15s ease;
  }
  .footer-card .social:hover { color: var(--text); }
  .footer-card .social .ti { font-size: 1.4rem; }
  .footer-card .social.casals img {
    width: 28px;
    height: 28px;
    display: block;
    object-fit: contain;
  }
  .footer-card .build-line {
    font-size: 0.75rem;
    color: var(--text-faint);
  }
  .footer-card .build-meta {
    font-size: 0.7rem;
    color: var(--text-faint);
    font-family: 'SF Mono', 'Fira Code', monospace;
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
    .brand-group { order: 1; }
    .actions { order: 2; margin-left: auto; }
    .search { order: 3; flex-basis: 100%; max-width: none; margin: 0; }
  }
</style>
