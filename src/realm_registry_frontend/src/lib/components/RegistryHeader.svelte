<script>
  import { createEventDispatcher } from 'svelte';
  import { _, locale } from 'svelte-i18n';
  import { supportedLocales, setLocale } from '$lib/i18n';

  export let searchQuery = '';
  export let isLoggedIn = false;
  export let userPrincipal = null;
  export let authLoading = false;
  export let panelOpen = false;
  export let marketplaceUrl = '';
  export let searchInput = null;

  const dispatch = createEventDispatcher();

  let showLanguageMenu = false;

  function handleSearchInput() {
    dispatch('search');
    if (searchQuery.trim()) {
      dispatch('openPanel');
    }
  }
</script>

<header class="registry-header">
  <div class="header-left">
    <a href="/" class="logo-link" aria-label="Realms">
      <img src="/images/logo_horizontal.svg" alt="Realms" class="logo" />
    </a>
  </div>

  <div class="header-center">
    <div class="search-wrapper">
      <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <circle cx="11" cy="11" r="8"></circle>
        <path d="m21 21-4.35-4.35"></path>
      </svg>
      <input
        bind:this={searchInput}
        type="search"
        class="search-input"
        placeholder={$_('search.placeholder')}
        aria-label={$_('search.placeholder')}
        bind:value={searchQuery}
        on:input={handleSearchInput}
        on:focus={() => dispatch('openPanel')}
      />
      {#if searchQuery}
        <button
          class="icon-btn search-clear"
          on:click={() => { searchQuery = ''; dispatch('search'); }}
          aria-label={$_('search.clear')}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6L6 18M6 6l12 12"></path>
          </svg>
        </button>
      {/if}
    </div>
  </div>

  <div class="header-right">
    <button
      class="btn btn-ghost browse-btn"
      class:active={panelOpen}
      on:click={() => dispatch('togglePanel')}
    >
      {$_('globe.browse_realms')}
    </button>

    {#if marketplaceUrl}
      <a href={marketplaceUrl} target="_blank" rel="noopener noreferrer" class="icon-btn" title={$_('controls.marketplace')} aria-label={$_('controls.marketplace')}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path>
          <line x1="3" y1="6" x2="21" y2="6"></line>
          <path d="M16 10a4 4 0 0 1-8 0"></path>
        </svg>
      </a>
    {/if}

    <a href="/create-realm" class="btn btn-primary create-btn">{$_('controls.create_realm')}</a>

    <div class="auth-section">
      {#if authLoading}
        <div class="auth-loading"></div>
      {:else if isLoggedIn}
        <a href="/my-dashboard" class="user-btn" title={userPrincipal?.toText()}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
          <span>{userPrincipal?.toText().slice(0, 5)}...{userPrincipal?.toText().slice(-3)}</span>
        </a>
        <button class="icon-btn" on:click={() => dispatch('logout')} title={$_('auth.logout')} aria-label={$_('auth.logout')}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
            <polyline points="16 17 21 12 16 7"></polyline>
            <line x1="21" y1="12" x2="9" y2="12"></line>
          </svg>
        </button>
      {:else}
        <button class="icon-btn" on:click={() => dispatch('login')} title={$_('auth.login')} aria-label={$_('auth.login')}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
        </button>
      {/if}
    </div>

    <div class="language-selector">
      <button class="icon-btn" on:click={() => (showLanguageMenu = !showLanguageMenu)} aria-label={$_('language.select')}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="2" y1="12" x2="22" y2="12"></line>
          <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
        </svg>
      </button>
      {#if showLanguageMenu}
        <div class="language-menu">
          {#each supportedLocales as loc}
            <button
              class="language-option"
              class:active={$locale === loc.id}
              on:click={() => { setLocale(loc.id); showLanguageMenu = false; }}
            >
              {loc.name}
            </button>
          {/each}
        </div>
      {/if}
    </div>
  </div>
</header>

<style>
  .registry-header {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 100;
    height: var(--header-height);
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0 1rem;
    background: rgba(255, 255, 255, 0.92);
    backdrop-filter: blur(8px);
    border-bottom: 1px solid var(--border);
    font-family: var(--font-family);
  }

  .header-left {
    flex-shrink: 0;
  }

  .logo-link {
    display: flex;
    align-items: center;
  }

  .logo {
    height: 28px;
    width: auto;
  }

  .header-center {
    flex: 1;
    max-width: 480px;
    margin: 0 auto;
  }

  .search-wrapper {
    position: relative;
    display: flex;
    align-items: center;
  }

  .search-icon {
    position: absolute;
    left: 0.75rem;
    color: var(--text-faint);
    pointer-events: none;
  }

  .search-input {
    width: 100%;
    height: 36px;
    padding: 0 2rem 0 2.25rem;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--surface);
    color: var(--text-primary);
    font-size: 0.875rem;
    font-family: inherit;
    outline: none;
    transition: border-color 0.15s;
  }

  .search-input:focus {
    border-color: var(--text-secondary);
  }

  .search-clear {
    position: absolute;
    right: 0.25rem;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-shrink: 0;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.4375rem 0.75rem;
    border-radius: 8px;
    font-size: 0.8125rem;
    font-weight: 500;
    font-family: inherit;
    text-decoration: none;
    cursor: pointer;
    border: none;
    transition: background 0.15s, color 0.15s;
    white-space: nowrap;
  }

  .btn-ghost {
    background: transparent;
    color: var(--text-secondary);
    border: 1px solid var(--border);
  }

  .btn-ghost:hover,
  .btn-ghost.active {
    background: var(--surface-2);
    color: var(--text-primary);
  }

  .btn-primary {
    background: var(--text-primary);
    color: var(--surface);
  }

  .btn-primary:hover {
    background: var(--text-secondary);
  }

  .icon-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    padding: 0;
    border: none;
    border-radius: 8px;
    background: transparent;
    color: var(--text-secondary);
    cursor: pointer;
    text-decoration: none;
    transition: background 0.15s;
  }

  .icon-btn:hover {
    background: var(--surface-2);
    color: var(--text-primary);
  }

  .user-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.25rem 0.5rem;
    border-radius: 8px;
    font-size: 0.75rem;
    font-family: ui-monospace, monospace;
    color: var(--text-secondary);
    text-decoration: none;
    background: var(--surface-2);
  }

  .user-btn:hover {
    background: var(--border);
  }

  .auth-loading {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: var(--surface-2);
    animation: pulse 1.2s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 0.5; }
    50% { opacity: 1; }
  }

  .language-selector {
    position: relative;
  }

  .language-menu {
    position: absolute;
    top: calc(100% + 4px);
    right: 0;
    min-width: 120px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    overflow: hidden;
    z-index: 200;
  }

  .language-option {
    display: block;
    width: 100%;
    padding: 0.5rem 0.75rem;
    border: none;
    background: transparent;
    text-align: left;
    font-size: 0.8125rem;
    color: var(--text-primary);
    cursor: pointer;
    font-family: inherit;
  }

  .language-option:hover,
  .language-option.active {
    background: var(--surface-2);
  }

  .browse-btn {
    display: none;
  }

  @media (min-width: 768px) {
    .browse-btn {
      display: inline-flex;
    }
    .create-btn span {
      display: inline;
    }
  }

  @media (max-width: 767px) {
    .header-center {
      max-width: none;
    }
    .create-btn {
      padding: 0.4375rem 0.5rem;
      font-size: 0.75rem;
    }
    .user-btn span {
      display: none;
    }
  }
</style>
