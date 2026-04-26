<script lang="ts">
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { page } from '$app/stores';
  import '../app.css';

  import { bootstrapAuth, isAuthenticated, login, logout, principalStore } from '$lib/auth';
  import { invalidateActors } from '$lib/canisters';

  let booted = false;
  let sidebarOpen = false;

  // @ts-ignore – Vite injects at build time
  let version = typeof __BUILD_VERSION__ !== 'undefined' ? __BUILD_VERSION__ : 'dev';
  // @ts-ignore
  let commitHash = typeof __BUILD_COMMIT__ !== 'undefined' ? __BUILD_COMMIT__ : 'local';
  // @ts-ignore
  let buildTime = typeof __BUILD_TIME__ !== 'undefined' ? __BUILD_TIME__ : '';

  onMount(async () => {
    if (!browser) return;
    await bootstrapAuth();
    booted = true;
  });

  async function handleLogin() {
    await login();
    invalidateActors();
  }

  async function handleLogout() {
    await logout();
    invalidateActors();
  }

  function shortPrincipal(text: string): string {
    if (text.length <= 15) return text;
    return text.slice(0, 7) + '...' + text.slice(-5);
  }

  $: routeIsActive = (path: string) => {
    if (path === '/') return $page.url.pathname === '/';
    return $page.url.pathname.startsWith(path);
  };

  const navItems = [
    { href: '/',          label: 'Dashboard',    icon: '⊞' },
    { href: '/platform',  label: 'Platform',     icon: '⚙' },
    { href: '/realms',    label: 'Realms',       icon: '◎' },
    { href: '/installer', label: 'Deployments',  icon: '⟐' },
  ];
</script>

<div class="shell" class:sidebar-open={sidebarOpen}>
  <aside class="sidebar">
    <div class="sidebar-brand">
      <span class="brand-icon">◈</span>
      <span class="brand-text">Platform</span>
    </div>
    <nav class="sidebar-nav">
      {#each navItems as item}
        <a
          href={item.href}
          class="nav-item"
          class:active={routeIsActive(item.href)}
          on:click={() => sidebarOpen = false}
        >
          <span class="nav-icon">{item.icon}</span>
          <span>{item.label}</span>
        </a>
      {/each}
    </nav>
    <div class="sidebar-footer">
      {#if !booted}
        <span class="muted">Loading...</span>
      {:else if $isAuthenticated && $principalStore}
        <div class="auth-info">
          <span class="who" title={$principalStore.toText()}>
            {shortPrincipal($principalStore.toText())}
          </span>
          <button class="btn btn-sm" on:click={handleLogout}>Sign out</button>
        </div>
      {:else}
        <button class="btn btn-primary btn-sm" style="width:100%" on:click={handleLogin}>
          Sign in
        </button>
      {/if}
      <div class="build-info">
        Platform Dashboard {version}{commitHash && commitHash !== 'local' ? ` (${commitHash})` : ''}{buildTime ? ` - ${buildTime}` : ''}
      </div>
    </div>
  </aside>

  <div class="main-area">
    <header class="topbar">
      <button class="hamburger" on:click={() => sidebarOpen = !sidebarOpen} aria-label="Toggle menu">
        <span></span><span></span><span></span>
      </button>
      <h1 class="topbar-title">
        {#each navItems as item}
          {#if routeIsActive(item.href)}
            {item.label}
          {/if}
        {/each}
      </h1>
      <div class="topbar-auth">
        {#if booted && !$isAuthenticated}
          <button class="btn btn-primary btn-sm" on:click={handleLogin}>Sign in</button>
        {:else if booted && $isAuthenticated && $principalStore}
          <span class="who-topbar">{shortPrincipal($principalStore.toText())}</span>
        {/if}
      </div>
    </header>
    <main class="content">
      <slot />
    </main>
  </div>
</div>

{#if sidebarOpen}
  <!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
  <div class="overlay" on:click={() => sidebarOpen = false}></div>
{/if}

<style>
  .shell {
    display: flex;
    min-height: 100vh;
  }

  /* Sidebar */
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: var(--sidebar-width);
    background: var(--surface);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    z-index: 40;
    transition: transform 0.2s ease;
  }
  .sidebar-brand {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 1rem 1.25rem;
    font-weight: 700;
    font-size: 1.05rem;
    border-bottom: 1px solid var(--border);
  }
  .brand-icon { font-size: 1.3rem; }
  .sidebar-nav {
    flex: 1;
    padding: 0.75rem 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }
  .nav-item {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    padding: 0.6rem 0.75rem;
    border-radius: 0.5rem;
    color: var(--text-muted);
    text-decoration: none;
    font-size: 0.9rem;
    transition: all 0.12s ease;
  }
  .nav-item:hover { background: var(--surface-2); color: var(--text); }
  .nav-item.active { background: var(--primary-light); color: var(--primary); font-weight: 600; }
  .nav-icon { font-size: 1.1rem; width: 1.3rem; text-align: center; }

  .sidebar-footer {
    padding: 1rem 1.25rem;
    border-top: 1px solid var(--border);
  }
  .build-info {
    margin-top: 0.75rem;
    font-size: 0.68rem;
    color: var(--text-faint, #999);
    text-align: center;
    line-height: 1.3;
  }
  .auth-info {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
  }
  .who {
    font-family: monospace;
    font-size: 0.78rem;
    color: var(--text-muted);
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* Main */
  .main-area {
    flex: 1;
    margin-left: var(--sidebar-width);
    display: flex;
    flex-direction: column;
    min-height: 100vh;
  }
  .topbar {
    position: sticky;
    top: 0;
    z-index: 30;
    height: var(--topbar-height);
    display: flex;
    align-items: center;
    padding: 0 1.5rem;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    gap: 1rem;
  }
  .topbar-title {
    font-size: 1rem;
    font-weight: 600;
    margin: 0;
    flex: 1;
  }
  .topbar-auth { display: flex; align-items: center; gap: 0.5rem; }
  .who-topbar { font-family: monospace; font-size: 0.8rem; color: var(--text-muted); }

  .content {
    flex: 1;
    padding: 1.75rem 2rem 3rem;
    max-width: 1200px;
    width: 100%;
  }

  .hamburger {
    display: none;
    flex-direction: column;
    gap: 4px;
    background: none;
    border: none;
    padding: 4px;
    cursor: pointer;
  }
  .hamburger span {
    width: 20px;
    height: 2px;
    background: var(--text-muted);
    border-radius: 1px;
  }

  .overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.3);
    z-index: 35;
  }
  .muted { color: var(--text-faint); font-size: 0.85rem; }

  @media (max-width: 768px) {
    .sidebar { transform: translateX(-100%); }
    .shell.sidebar-open .sidebar { transform: translateX(0); }
    .main-area { margin-left: 0; }
    .hamburger { display: flex; }
    .overlay { display: block; }
    .content { padding: 1.25rem 1rem 2rem; }
  }
</style>
