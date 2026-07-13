<script>
  import { createEventDispatcher, onMount } from 'svelte';
  import { _, locale } from 'svelte-i18n';
  import { supportedLocales, setLocale } from '$lib/i18n';
  import { requestRegistryTour } from '$lib/registry-tour.js';

  export let isLoggedIn = false;
  export let userPrincipal = null;
  export let authLoading = false;
  export let marketplaceUrl = '';
  export let casalsUrl = '';

  const dispatch = createEventDispatcher();
  const CASALS_FALLBACK_URL = 'https://mcqbx-hyaaa-aaaaj-qsarq-cai.icp0.io';

  $: architectureUrl = casalsUrl || CASALS_FALLBACK_URL;

  let showLanguageMenu = false;
  let showAuthMenu = false;

  $: principalText = userPrincipal?.toText?.() || '';
  $: principalShort = principalText
    ? `${principalText.slice(0, 5)}…${principalText.slice(-3)}`
    : '';

  function closePopovers() {
    showLanguageMenu = false;
    showAuthMenu = false;
  }

  function openTour() {
    closePopovers();
    requestRegistryTour();
  }

  function onDocClick(e) {
    const keepOpen = e.target?.closest?.('.icon-rail');
    if (!keepOpen) {
      closePopovers();
    }
  }

  function onDocKeydown(e) {
    if (e.key !== 'Escape') return;
    if (!showLanguageMenu && !showAuthMenu) return;
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

<nav class="icon-rail" aria-label="Main" data-tour="top-rail">
  <button
    type="button"
    class="rail-btn"
    title={$_('tour.start')}
    aria-label={$_('tour.start')}
    on:click|stopPropagation={openTour}
  >
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10"></circle>
      <path d="M9.09 9a3 3 0 1 1 5.82 1c0 2-3 2-3 4"></path>
      <line x1="12" y1="17" x2="12.01" y2="17"></line>
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

  <a
    href={architectureUrl}
    target="_blank"
    rel="noopener noreferrer"
    class="rail-btn"
    title={$_('controls.architecture')}
    aria-label={$_('controls.architecture')}
  >
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <line x1="6" y1="18" x2="6" y2="11"></line>
      <line x1="10" y1="18" x2="10" y2="11"></line>
      <line x1="14" y1="18" x2="14" y2="11"></line>
      <line x1="18" y1="18" x2="18" y2="11"></line>
      <line x1="2" y1="21" x2="22" y2="21"></line>
      <line x1="4" y1="18" x2="20" y2="18"></line>
      <path d="M12 3v5"></path>
      <path d="M8 8h8"></path>
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

    {#if showLanguageMenu}
      <div class="floating-menu" role="menu" on:mousedown|stopPropagation>
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
  </div>

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

      {#if showAuthMenu}
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

  .floating-menu {
    position: absolute;
    top: calc(100% + 0.5rem);
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

  @media (max-width: 900px) {
    .rail-btn {
      width: 56px;
      height: 56px;
    }

    .rail-btn :global(svg) {
      width: 24px;
      height: 24px;
    }
  }

  @media (max-width: 480px) {
    .icon-rail {
      gap: 0.4rem;
      top: 0.75rem;
      left: 50%;
      transform: translateX(-50%);
      width: auto;
      max-width: calc(100vw - 1.5rem);
      pointer-events: none;
      padding: 0 2px;
      overflow: visible;
    }

    .rail-btn {
      width: 40px;
      height: 40px;
    }

    .rail-btn :global(svg) {
      width: 18px;
      height: 18px;
    }
  }
</style>
