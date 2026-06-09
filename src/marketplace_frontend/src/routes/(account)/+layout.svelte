<script lang="ts">
  import { _ } from 'svelte-i18n';
  import { page } from '$app/stores';

  $: active = (path: string) => $page.url.pathname.startsWith(path);
</script>

<div class="account">
  <aside class="sidebar">
    <nav class="side-nav" aria-label="Account navigation">
      <a class="item" href="/my-purchases" class:active={active('/my-purchases')}>
        <i class="ti ti-shopping-bag" aria-hidden="true"></i>
        <span>{$_('nav.my_purchases')}</span>
      </a>
      <a class="item" href="/upload" class:active={active('/upload')}>
        <i class="ti ti-upload" aria-hidden="true"></i>
        <span>{$_('nav.upload')}</span>
      </a>
      <a class="item" href="/developer" class:active={active('/developer')}>
        <i class="ti ti-code" aria-hidden="true"></i>
        <span>{$_('nav.developer')}</span>
      </a>
    </nav>
  </aside>

  <div class="content">
    <slot />
  </div>
</div>

<style>
  .account {
    display: grid;
    grid-template-columns: 200px 1fr;
    gap: 2rem;
    align-items: flex-start;
  }
  .sidebar {
    position: sticky;
    top: 80px;
  }
  .side-nav {
    display: flex;
    flex-direction: column;
    gap: 2px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 0.75rem;
    padding: 0.5rem;
  }
  .item {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    padding: 0.65rem 0.85rem;
    border-radius: 0.5rem;
    color: var(--text-muted);
    text-decoration: none;
    font-size: 0.9rem;
    transition: all 0.12s ease;
  }
  .item:hover { background: var(--surface-2); color: var(--text); }
  .item.active { background: var(--surface-2); color: var(--text); font-weight: 500; }
  .item .ti { font-size: 1.1rem; flex-shrink: 0; }
  .content { min-width: 0; }

  @media (max-width: 760px) {
    .account { grid-template-columns: 1fr; gap: 1rem; }
    .sidebar { position: static; }
    .side-nav { flex-direction: row; overflow-x: auto; padding: 0.4rem; }
    .item { padding: 0.5rem 0.75rem; white-space: nowrap; font-size: 0.85rem; }
  }
</style>
