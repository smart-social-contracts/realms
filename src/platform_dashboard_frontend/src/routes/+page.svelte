<script lang="ts">
  import { onMount } from 'svelte';
  import { registryActor, marketplaceActor, fileRegistryActor, installerActor } from '$lib/canisters';
  import type { StatusRecord, FileRegistryStats } from '$lib/types';

  let loading = true;
  let error = '';
  let realmsCount = 0;
  let marketplaceStats: Record<string, any> = {};
  let fileStats: FileRegistryStats | null = null;
  let installerHealthy = false;

  onMount(async () => {
    try {
      const results = await Promise.allSettled([
        registryActor.status(),
        marketplaceActor.status(),
        fileRegistryActor.get_stats(),
        installerActor.health(),
      ]);

      if (results[0].status === 'fulfilled') {
        const s = results[0].value?.Ok ?? results[0].value;
        realmsCount = s?.realms_count ?? 0;
      }

      if (results[1].status === 'fulfilled') {
        const s = results[1].value?.Ok ?? results[1].value;
        marketplaceStats = s ?? {};
      }

      if (results[2].status === 'fulfilled') {
        const raw = results[2].value?.Ok ?? results[2].value;
        try {
          fileStats = typeof raw === 'string' ? JSON.parse(raw) : raw;
        } catch { fileStats = null; }
      }

      if (results[3].status === 'fulfilled') {
        installerHealthy = true;
      }
    } catch (e: any) {
      error = e.message || 'Failed to load dashboard data';
    } finally {
      loading = false;
    }
  });

  function formatBytes(bytes: number): string {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i];
  }
</script>

<h1 class="page-title">Dashboard</h1>
<p class="page-subtitle">Platform overview across all subsystems</p>

{#if loading}
  <div class="empty-state"><span class="spinner"></span> Loading...</div>
{:else if error}
  <div class="card" style="border-color: var(--danger); color: var(--danger);">{error}</div>
{:else}
  <div class="stat-grid">
    <div class="stat-card">
      <div class="stat-value">{realmsCount}</div>
      <div class="stat-label">Realms Registered</div>
    </div>

    <div class="stat-card">
      <div class="stat-value">{marketplaceStats.extensions_count ?? '—'}</div>
      <div class="stat-label">Marketplace Extensions</div>
    </div>

    <div class="stat-card">
      <div class="stat-value">{marketplaceStats.codices_count ?? '—'}</div>
      <div class="stat-label">Codices</div>
    </div>

    <div class="stat-card">
      <div class="stat-value">{marketplaceStats.assistants_count ?? '—'}</div>
      <div class="stat-label">Assistants</div>
    </div>

    <div class="stat-card">
      <div class="stat-value">
        {fileStats ? formatBytes(fileStats.total_bytes) : '—'}
      </div>
      <div class="stat-label">File Registry Storage</div>
    </div>

    <div class="stat-card">
      <div class="stat-value">{fileStats?.total_files ?? '—'}</div>
      <div class="stat-label">Files Stored</div>
    </div>

    <div class="stat-card">
      <div class="stat-value">
        <span class="badge" class:badge-success={installerHealthy} class:badge-danger={!installerHealthy}>
          {installerHealthy ? 'Healthy' : 'Unreachable'}
        </span>
      </div>
      <div class="stat-label">Installer Status</div>
    </div>

    <div class="stat-card">
      <div class="stat-value">4</div>
      <div class="stat-label">Platform Subsystems</div>
    </div>
  </div>

  <h2 style="font-size: 1.1rem; margin-bottom: 1rem;">Quick Links</h2>
  <div class="quick-links">
    <a href="/platform" class="card quick-link">
      <span class="ql-icon">⚙</span>
      <span class="ql-text">
        <strong>Platform Canisters</strong>
        <span>Registry, Installer, Marketplace, File Registry</span>
      </span>
    </a>
    <a href="/realms" class="card quick-link">
      <span class="ql-icon">◎</span>
      <span class="ql-text">
        <strong>Browse Realms</strong>
        <span>{realmsCount} realm{realmsCount !== 1 ? 's' : ''} registered</span>
      </span>
    </a>
    <a href="/installer" class="card quick-link">
      <span class="ql-icon">⟐</span>
      <span class="ql-text">
        <strong>Installer</strong>
        <span>Deployments and health status</span>
      </span>
    </a>
  </div>
{/if}

<style>
  .quick-links {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1rem;
  }
  .quick-link {
    display: flex;
    align-items: center;
    gap: 1rem;
    text-decoration: none;
    cursor: pointer;
  }
  .ql-icon { font-size: 1.6rem; }
  .ql-text {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }
  .ql-text strong { font-size: 0.95rem; }
  .ql-text span { font-size: 0.8rem; color: var(--text-muted); }
</style>
