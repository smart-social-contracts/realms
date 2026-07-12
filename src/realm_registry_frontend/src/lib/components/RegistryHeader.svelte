<script>
  import { createEventDispatcher, onMount } from 'svelte';
  import { _, locale } from 'svelte-i18n';
  import { supportedLocales, setLocale } from '$lib/i18n';
  import { requestAssistantToggle } from '$lib/assistant-open.js';

  export let searchQuery = '';
  export let isLoggedIn = false;
  export let userPrincipal = null;
  export let authLoading = false;
  export let panelOpen = false;
  export let marketplaceUrl = '';
  export let searchInput = null;

  const dispatch = createEventDispatcher();

  let showLanguageMenu = false;
  let showSearch = false;
  let showAuthMenu = false;
  let showAbout = false;

  const GITHUB_URL = 'https://github.com/smart-social-contracts/realms';

  $: principalText = userPrincipal?.toText?.() || '';
  $: principalShort = principalText
    ? `${principalText.slice(0, 5)}…${principalText.slice(-3)}`
    : '';

  function handleSearchInput() {
    dispatch('search');
    if (searchQuery.trim()) {
      dispatch('openPanel');
    }
  }

  function openSearch() {
    showSearch = !showSearch;
    showLanguageMenu = false;
    showAuthMenu = false;
    showAbout = false;
    if (showSearch) {
      dispatch('openPanel');
      requestAnimationFrame(() => searchInput?.focus());
    }
  }

  function closePopovers() {
    showLanguageMenu = false;
    showAuthMenu = false;
    showSearch = false;
  }

  function openAbout() {
    closePopovers();
    showAbout = true;
  }

  function cancelSearch() {
    showSearch = false;
  }

  function handleSearchKeydown(e) {
    if (e.key === 'Escape') {
      e.preventDefault();
      cancelSearch();
      return;
    }
    if (e.key === 'Enter') {
      e.preventDefault();
      dispatch('acceptSearch');
      showSearch = false;
    }
  }

  function onDocClick(e) {
    const keepOpen = e.target?.closest?.('.icon-rail, .floating-menu, .search-stage, .about-modal');
    if (!keepOpen) {
      closePopovers();
      showAbout = false;
    }
  }

  function onDocKeydown(e) {
    if (e.key !== 'Escape') return;
    if (showAbout) {
      e.preventDefault();
      showAbout = false;
      return;
    }
    if (!showSearch && !showLanguageMenu && !showAuthMenu) return;
    e.preventDefault();
    closePopovers();
  }

  onMount(() => {
    document.addEventListener('click', onDocClick);
    document.addEventListener('keydown', onDocKeydown);
    return () => {
      document.removeEventListener('click', onDocClick);
      document.removeEventListener('keydown', onDocKeydown);
    };
  });
</script>

<nav class="icon-rail" aria-label="Main">
  <button
    type="button"
    class="rail-btn rail-btn-logo"
    title={$_('about.title')}
    aria-label={$_('about.title')}
    aria-haspopup="dialog"
    aria-expanded={showAbout}
    on:click|stopPropagation={openAbout}
  >
    <img src="/images/logo_sphere_only.svg" alt="" class="rail-logo" />
  </button>

  <div class="rail-item">
    <button
      type="button"
      class="rail-btn"
      class:active={showSearch || Boolean(searchQuery)}
      on:click|stopPropagation={openSearch}
      title={$_('search.placeholder')}
      aria-label={$_('search.placeholder')}
      aria-expanded={showSearch}
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <circle cx="11" cy="11" r="8"></circle>
        <path d="m21 21-4.35-4.35"></path>
      </svg>
    </button>
  </div>

  <button
    type="button"
    class="rail-btn"
    class:active={panelOpen}
    on:click={() => {
      closePopovers();
      showSearch = false;
      showAbout = false;
      dispatch('togglePanel');
    }}
    title={$_('globe.browse_realms')}
    aria-label={$_('globe.browse_realms')}
  >
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
      <line x1="8" y1="6" x2="21" y2="6"></line>
      <line x1="8" y1="12" x2="21" y2="12"></line>
      <line x1="8" y1="18" x2="21" y2="18"></line>
      <circle cx="4" cy="6" r="1.2" fill="currentColor" stroke="none"></circle>
      <circle cx="4" cy="12" r="1.2" fill="currentColor" stroke="none"></circle>
      <circle cx="4" cy="18" r="1.2" fill="currentColor" stroke="none"></circle>
    </svg>
  </button>

  {#if marketplaceUrl}
    <a
      href={marketplaceUrl}
      target="_blank"
      rel="noopener noreferrer"
      class="rail-btn"
      title={$_('controls.marketplace')}
      aria-label={$_('controls.marketplace')}
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path>
        <line x1="3" y1="6" x2="21" y2="6"></line>
        <path d="M16 10a4 4 0 0 1-8 0"></path>
      </svg>
    </a>
  {/if}

  <a
    href="/create-realm"
    class="rail-btn"
    title={$_('controls.create_realm')}
    aria-label={$_('controls.create_realm')}
  >
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
      <line x1="12" y1="5" x2="12" y2="19"></line>
      <line x1="5" y1="12" x2="19" y2="12"></line>
    </svg>
  </a>

  <div class="rail-item">
    <button
      type="button"
      class="rail-btn"
      class:active={showLanguageMenu}
      on:click|stopPropagation={() => {
        showLanguageMenu = !showLanguageMenu;
        showAuthMenu = false;
        showSearch = false;
        showAbout = false;
      }}
      title={$_('language.select')}
      aria-label={$_('language.select')}
      aria-expanded={showLanguageMenu}
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="2" y1="12" x2="22" y2="12"></line>
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
      </svg>
    </button>
  </div>

  <button
    type="button"
    class="rail-btn rail-btn-ai"
    on:click={() => {
      closePopovers();
      showSearch = false;
      showAbout = false;
      requestAssistantToggle();
    }}
    title={$_('assistant.toggle', { default: 'AI Assistant' })}
    aria-label={$_('assistant.toggle', { default: 'AI Assistant' })}
  >
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M12 5a3 3 0 1 0-5.997.125 4 4 0 0 0-2.526 5.77 4 4 0 0 0 .556 6.588A4 4 0 1 0 12 18Z"></path>
      <path d="M12 5a3 3 0 1 1 5.997.125 4 4 0 0 1 2.526 5.77 4 4 0 0 1-.556 6.588A4 4 0 1 1 12 18Z"></path>
      <path d="M15 13a4.5 4.5 0 0 1-3-4 4.5 4.5 0 0 1-3 4"></path>
      <path d="M12 21v-3"></path>
    </svg>
  </button>

  <div class="rail-item">
    {#if authLoading}
      <div class="rail-btn rail-loading" aria-hidden="true"></div>
    {:else if isLoggedIn}
      <button
        type="button"
        class="rail-btn rail-btn-logged"
        class:active={showAuthMenu}
        on:click|stopPropagation={() => {
          showAuthMenu = !showAuthMenu;
          showLanguageMenu = false;
          showSearch = false;
          showAbout = false;
        }}
        title={principalText || $_('auth.account')}
        aria-label={$_('auth.account')}
        aria-expanded={showAuthMenu}
      >
        <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
          <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
        </svg>
        <span class="auth-status-dot" aria-hidden="true"></span>
      </button>
    {:else}
      <button
        type="button"
        class="rail-btn"
        on:click={() => dispatch('login')}
        title={$_('auth.login')}
        aria-label={$_('auth.login')}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
          <circle cx="12" cy="7" r="4"></circle>
        </svg>
      </button>
    {/if}
  </div>
</nav>

{#if showLanguageMenu}
  <div class="floating-menu language-menu" role="menu" on:mousedown|stopPropagation>
    {#each supportedLocales as loc (loc.id)}
      <button
        type="button"
        class="menu-option"
        role="menuitem"
        class:active={$locale === loc.id}
        on:click={() => {
          setLocale(loc.id);
          showLanguageMenu = false;
        }}
      >
        {loc.name}
      </button>
    {/each}
  </div>
{/if}

{#if showAuthMenu && isLoggedIn}
  <div class="floating-menu auth-menu" role="menu" on:mousedown|stopPropagation>
    {#if principalShort}
      <div class="menu-meta" title={principalText}>{$_('auth.signed_in')}: {principalShort}</div>
    {/if}
    <a href="/my-dashboard" class="menu-option" role="menuitem" on:click={() => (showAuthMenu = false)}>
      {$_('dashboard.title')}
    </a>
    <button
      type="button"
      class="menu-option menu-option-danger"
      role="menuitem"
      on:click={() => {
        showAuthMenu = false;
        dispatch('logout');
      }}
    >
      {$_('auth.logout')}
    </button>
  </div>
{/if}

{#if showSearch}
  <div
    class="search-stage"
    role="presentation"
    on:mousedown={() => {
      showSearch = false;
    }}
  >
    <div
      class="search-popover search-popover-center"
      role="search"
      on:mousedown|stopPropagation
    >
      <svg class="search-field-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <circle cx="11" cy="11" r="8"></circle>
        <path d="m21 21-4.35-4.35"></path>
      </svg>
      <input
        bind:this={searchInput}
        type="text"
        class="search-input"
        placeholder={$_('search.placeholder')}
        aria-label={$_('search.placeholder')}
        bind:value={searchQuery}
        on:input={handleSearchInput}
        on:keydown={handleSearchKeydown}
        autocomplete="off"
        spellcheck="false"
      />
      {#if searchQuery}
        <button
          type="button"
          class="clear-btn"
          on:click={() => {
            searchQuery = '';
            dispatch('search');
            searchInput?.focus();
          }}
          aria-label={$_('search.clear')}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6L6 18M6 6l12 12"></path>
          </svg>
        </button>
      {/if}
    </div>
  </div>
{/if}

{#if showAbout}
  <div
    class="about-overlay"
    role="presentation"
    on:mousedown={() => (showAbout = false)}
  >
    <div
      class="about-modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="about-title"
      tabindex="-1"
      on:mousedown|stopPropagation
    >
      <button
        type="button"
        class="about-close"
        on:click={() => (showAbout = false)}
        aria-label={$_('about.close')}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M18 6L6 18M6 6l12 12"></path>
        </svg>
      </button>
      <img src="/images/logo_sphere_only.svg" alt="" class="about-logo" />
      <h2 id="about-title" class="about-title">{$_('about.title')}</h2>
      <p class="about-body">{$_('about.body')}</p>
      <div class="about-actions">
        <button type="button" class="about-btn" on:click={() => (showAbout = false)}>
          {$_('about.close')}
        </button>
        <a
          href={GITHUB_URL}
          target="_blank"
          rel="noopener noreferrer"
          class="about-github"
          aria-label={$_('about.github')}
          title={$_('about.github')}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.387.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.387-1.333-1.756-1.333-1.756-1.09-.745.083-.729.083-.729 1.205.085 1.84 1.237 1.84 1.237 1.07 1.834 2.807 1.304 3.492.997.108-.775.418-1.305.76-1.605-2.665-.303-5.466-1.332-5.466-5.93 0-1.31.468-2.382 1.236-3.222-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.3 1.23.96-.267 1.98-.4 3-.405 1.02.005 2.04.138 3 .405 2.29-1.552 3.297-1.23 3.297-1.23.653 1.652.242 2.873.118 3.176.77.84 1.235 1.912 1.235 3.222 0 4.61-2.807 5.624-5.48 5.92.43.37.823 1.102.823 2.222 0 1.606-.015 2.896-.015 3.286 0 .32.216.694.825.576C20.565 21.796 24 17.297 24 12c0-6.63-5.37-12-12-12z"/>
          </svg>
        </a>
      </div>
    </div>
  </div>
{/if}

<style>
  .icon-rail {
    position: fixed;
    top: 1rem;
    left: 50%;
    transform: translateX(-50%);
    z-index: 200;
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 0.75rem;
    pointer-events: none;
    max-width: calc(100vw - 1.5rem);
    overflow: visible;
  }

  .rail-item {
    position: relative;
    pointer-events: auto;
    flex-shrink: 0;
  }

  .rail-btn {
    pointer-events: auto;
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 60px;
    height: 60px;
    padding: 0;
    border: none;
    border-radius: 50%;
    background: rgba(229, 229, 229, 0.55);
    color: #171717;
    cursor: pointer;
    text-decoration: none;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    transition: background 0.15s ease, transform 0.15s ease, color 0.15s ease;
    box-shadow: none;
  }

  .rail-btn :global(svg) {
    width: 24px;
    height: 24px;
  }

  .rail-btn:hover {
    background: rgba(212, 212, 212, 0.72);
    transform: scale(1.04);
  }

  .rail-btn.active {
    background: rgba(212, 212, 212, 0.8);
    color: #0a0a0a;
  }

  .rail-btn-ai {
    background: rgba(17, 17, 17, 0.82);
    color: #ffffff;
    animation: ai-glow 4.5s ease-in-out 1.2s infinite;
  }

  .rail-btn-ai:hover {
    background: rgba(38, 38, 38, 0.9);
    animation: none;
  }

  @keyframes ai-glow {
    0%,
    72%,
    100% {
      box-shadow: 0 0 0 0 rgba(17, 17, 17, 0);
      transform: scale(1);
    }
    80% {
      box-shadow:
        0 0 0 4px rgba(17, 17, 17, 0.12),
        0 0 18px 2px rgba(17, 17, 17, 0.28);
      transform: scale(1.04);
    }
    88% {
      box-shadow:
        0 0 0 8px rgba(17, 17, 17, 0.04),
        0 0 28px 4px rgba(17, 17, 17, 0.18);
      transform: scale(1.02);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .rail-btn-ai,
    .rail-btn-logo {
      animation: none;
    }
  }

  .rail-btn-logo {
    background: transparent;
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
    animation: logo-glimpse 5.5s ease-in-out 1.5s infinite;
  }

  .rail-btn-logo:hover,
  .rail-btn-logo.active {
    background: transparent;
    transform: scale(1.08);
    animation: none;
  }

  @keyframes logo-glimpse {
    0%,
    68%,
    100% {
      filter: brightness(1);
      transform: scale(1);
      opacity: 1;
    }
    76% {
      filter: brightness(1.45);
      transform: scale(1.1);
      opacity: 1;
    }
    84% {
      filter: brightness(1.15);
      transform: scale(1.04);
      opacity: 1;
    }
  }

  .rail-logo {
    width: 100%;
    height: 100%;
    max-width: 52px;
    max-height: 52px;
    object-fit: contain;
    pointer-events: none;
  }

  .rail-btn-logged {
    background: rgba(17, 17, 17, 0.88);
    color: #ffffff;
    position: relative;
  }

  .rail-btn-logged:hover,
  .rail-btn-logged.active {
    background: rgba(38, 38, 38, 0.95);
    color: #ffffff;
  }

  .rail-btn-logged :global(svg) {
    width: 22px;
    height: 22px;
  }

  .auth-status-dot {
    position: absolute;
    right: 10px;
    bottom: 10px;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #22c55e;
    border: 2px solid #fafafa;
    box-shadow: 0 0 0 1px rgba(34, 197, 94, 0.35);
  }

  .menu-meta {
    padding: 0.45rem 0.7rem 0.35rem;
    font-size: 0.6875rem;
    color: #737373;
    font-family: ui-monospace, monospace;
    word-break: break-all;
  }

  .menu-option-danger {
    color: #b91c1c;
  }

  .about-overlay {
    position: fixed;
    inset: 0;
    z-index: 300;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem;
    background: rgba(0, 0, 0, 0.18);
  }

  .about-modal {
    position: relative;
    width: min(420px, calc(100vw - 2rem));
    padding: 1.75rem 1.5rem 1.35rem;
    background: rgba(255, 255, 255, 0.82);
    border: 1px solid rgba(229, 229, 229, 0.9);
    border-radius: 16px;
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.12);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    text-align: center;
    font-family: inherit;
  }

  .about-close {
    position: absolute;
    top: 0.75rem;
    right: 0.75rem;
    width: 32px;
    height: 32px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: none;
    border-radius: 8px;
    background: transparent;
    color: #737373;
    cursor: pointer;
  }

  .about-close:hover {
    background: #f5f5f5;
    color: #171717;
  }

  .about-logo {
    width: 56px;
    height: 56px;
    object-fit: contain;
    margin: 0 auto 0.85rem;
    display: block;
  }

  .about-title {
    margin: 0 0 0.75rem;
    font-size: 1.125rem;
    font-weight: 600;
    color: #171717;
  }

  .about-body {
    margin: 0 0 1.25rem;
    font-size: 0.9375rem;
    line-height: 1.55;
    color: #525252;
    text-align: left;
    white-space: pre-line;
  }

  .about-actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
  }

  .about-btn {
    border: 1px solid #e5e5e5;
    border-radius: 8px;
    background: #f5f5f5;
    color: #171717;
    font-size: 0.8125rem;
    font-family: inherit;
    font-weight: 500;
    padding: 0.5rem 0.9rem;
    cursor: pointer;
  }

  .about-btn:hover {
    background: #e5e5e5;
  }

  .about-github {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    color: #171717;
    background: #f5f5f5;
    text-decoration: none;
  }

  .about-github:hover {
    background: #e5e5e5;
  }

  .rail-loading {
    opacity: 0.55;
    animation: pulse 1.2s ease-in-out infinite;
    pointer-events: none;
  }

  @keyframes pulse {
    0%,
    100% {
      opacity: 0.4;
    }
    50% {
      opacity: 0.85;
    }
  }

  .rail-popover {
    display: none;
  }

  .floating-menu {
    position: fixed;
    top: calc(1rem + 60px + 0.75rem);
    left: 50%;
    transform: translateX(-50%);
    z-index: 230;
    min-width: 160px;
    padding: 0.35rem;
    background: rgba(255, 255, 255, 0.98);
    border: 1px solid #e5e5e5;
    border-radius: 12px;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.12);
    backdrop-filter: blur(10px);
    pointer-events: auto;
  }

  .menu-option {
    display: block;
    width: 100%;
    padding: 0.55rem 0.7rem;
    border: none;
    border-radius: 8px;
    background: transparent;
    text-align: left;
    font-size: 0.8125rem;
    font-family: inherit;
    color: #171717;
    text-decoration: none;
    cursor: pointer;
  }

  .menu-option:hover,
  .menu-option.active {
    background: #f5f5f5;
  }

  .search-stage {
    position: fixed;
    inset: 0;
    z-index: 220;
    display: flex;
    align-items: center;
    justify-content: center;
    pointer-events: auto;
    background: transparent;
  }

  .search-popover {
    display: flex;
    align-items: center;
    width: min(420px, calc(100vw - 2rem));
    padding: 0.55rem 0.65rem 0.55rem 0.9rem;
    background: #ffffff;
    border: 1px solid #e5e5e5;
    border-radius: 16px;
    box-shadow: 0 16px 48px rgba(0, 0, 0, 0.12);
  }

  .search-popover-center {
    position: relative;
    left: auto;
    top: auto;
    transform: none;
  }

  .search-field-icon {
    flex-shrink: 0;
    color: #a3a3a3;
    margin-right: 0.35rem;
  }

  .search-input {
    flex: 1;
    min-width: 0;
    height: 40px;
    border: none;
    outline: none;
    background: transparent;
    font-size: 1rem;
    font-family: inherit;
    color: #171717;
  }

  .search-input::-webkit-search-cancel-button,
  .search-input::-webkit-search-decoration,
  .search-input::-ms-clear {
    -webkit-appearance: none;
    appearance: none;
    display: none;
    width: 0;
    height: 0;
  }

  .clear-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border: none;
    border-radius: 50%;
    background: transparent;
    color: #737373;
    cursor: pointer;
  }

  .clear-btn:hover {
    background: #f5f5f5;
    color: #171717;
  }

  .menu-popover {
    min-width: 140px;
    padding: 0.35rem;
    overflow: hidden;
  }

  .menu-option {
    display: block;
    width: 100%;
    padding: 0.55rem 0.7rem;
    border: none;
    border-radius: 8px;
    background: transparent;
    text-align: left;
    font-size: 0.8125rem;
    font-family: inherit;
    color: #171717;
    text-decoration: none;
    cursor: pointer;
  }

  .menu-option:hover,
  .menu-option.active {
    background: #f5f5f5;
  }

  @media (max-width: 900px) {
    .floating-menu {
      top: calc(1rem + 56px + 0.75rem);
    }

    .rail-btn {
      width: 56px;
      height: 56px;
    }

    .rail-btn :global(svg) {
      width: 24px;
      height: 24px;
    }

    .rail-logo {
      max-width: 48px;
      max-height: 48px;
    }
  }

  @media (max-width: 480px) {
    .icon-rail {
      gap: 0.4rem;
      top: 0.75rem;
      left: 0.75rem;
      right: 0.75rem;
      transform: none;
      width: auto;
      max-width: none;
      pointer-events: auto;
      padding: 0 2px;
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
      scrollbar-width: none;
      mask-image: linear-gradient(90deg, transparent 0, #000 12px, #000 calc(100% - 12px), transparent 100%);
      -webkit-mask-image: linear-gradient(90deg, transparent 0, #000 12px, #000 calc(100% - 12px), transparent 100%);
    }

    .icon-rail::-webkit-scrollbar {
      display: none;
    }

    .floating-menu {
      top: calc(0.75rem + 40px + 0.5rem);
    }

    .rail-btn {
      width: 40px;
      height: 40px;
    }

    .rail-btn :global(svg) {
      width: 18px;
      height: 18px;
    }

    .rail-logo {
      max-width: 36px;
      max-height: 36px;
    }
  }
</style>
