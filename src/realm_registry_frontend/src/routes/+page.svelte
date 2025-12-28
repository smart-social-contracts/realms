<script>
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';

  let backend;
  let realms = [];
  let loading = true;
  let error = null;
  let searchQuery = '';
  let filteredRealms = [];
  let showAddForm = false;
  let newRealm = { id: '', name: '', url: '', logo: '' };
  let addingRealm = false;

  // Get commit hash from meta tag
  let commitHash = '';
  // Get commit datetime from meta tag
  let commitDatetime = '';
  // Get version from meta tag
  let version = '';

  onMount(async () => {
    if (browser) {
      // Only import backend in browser context
      const { backend: b } = await import("$lib/canisters");
      backend = b;
      await loadRealms();
      
      // Get version info from meta tags
      const commitHashMeta = document.querySelector('meta[name="commit-hash"]');
      if (commitHashMeta) {
        commitHash = commitHashMeta.getAttribute('content') || '';
        // Format to show only first 7 characters if it's a full hash
        if (commitHash && commitHash !== 'COMMIT_HASH_PLACEHOLDER' && commitHash.length > 7) {
          commitHash = commitHash.substring(0, 7);
        }
      }
      
      const commitDatetimeMeta = document.querySelector('meta[name="commit-datetime"]');
      if (commitDatetimeMeta) {
        commitDatetime = commitDatetimeMeta.getAttribute('content') || '';
      }
      
      const versionMeta = document.querySelector('meta[name="version"]');
      if (versionMeta) {
        version = versionMeta.getAttribute('content') || '';
      }
    }
  });

  async function loadRealms() {
    try {
      loading = true;
      error = null;
      const response = await backend.list_realms();
      realms = response || [];
      filteredRealms = realms;
      loading = false;
      // Fetch user counts from each realm's status endpoint
      fetchUserCounts();
    } catch (err) {
      error = err.message || 'Failed to load realms';
      loading = false;
    }
  }

  function isLocalDevelopment() {
    return window.location.hostname.includes('localhost') || window.location.hostname.includes('127.0.0.1');
  }

  async function fetchUserCounts() {
    // Fetch user counts from each realm's backend via Candid
    const { Actor, HttpAgent } = await import('@dfinity/agent');
    const { Principal } = await import('@dfinity/principal');
    
    // Minimal IDL for the status method - only need users_count from the response
    const { IDL } = await import('@dfinity/candid');
    
    const statusIdlFactory = ({ IDL }) => {
      const StatusData = IDL.Record({
        'status': IDL.Text,
        'demo_mode': IDL.Bool,
        'transfers_count': IDL.Nat,
        'codexes_count': IDL.Nat,
        'proposals_count': IDL.Nat,
        'realms_count': IDL.Nat,
        'version': IDL.Text,
        'extensions': IDL.Vec(IDL.Text),
        'disputes_count': IDL.Nat,
        'commit': IDL.Text,
        'instruments_count': IDL.Nat,
        'organizations_count': IDL.Nat,
        'mandates_count': IDL.Nat,
        'tasks_count': IDL.Nat,
        'votes_count': IDL.Nat,
        'licenses_count': IDL.Nat,
        'users_count': IDL.Nat,
        'trades_count': IDL.Nat,
      });
      const ApiResponse = IDL.Record({
        'data': IDL.Variant({ 'status': StatusData }),
        'success': IDL.Bool,
      });
      return IDL.Service({
        'status': IDL.Func([], [ApiResponse], ['query']),
      });
    };
    
    const host = isLocalDevelopment() 
      ? 'http://localhost:8000' 
      : 'https://icp0.io';
    
    const updates = await Promise.allSettled(
      realms.map(async (realm) => {
        try {
          const agent = new HttpAgent({ host });
          
          // Fetch root key for local development
          if (isLocalDevelopment()) {
            await agent.fetchRootKey();
          }
          
          const actor = Actor.createActor(statusIdlFactory, {
            agent,
            canisterId: Principal.fromText(realm.id),
          });
          
          const response = await actor.status();
          if (response.success && response.data.status) {
            const usersCount = Number(response.data.status.users_count);
            return { id: realm.id, users_count: usersCount };
          }
        } catch (e) {
          console.debug(`Could not fetch status for ${realm.id}:`, e.message);
        }
        return null;
      })
    );
    
    // Update realms with fetched counts
    updates.forEach(result => {
      if (result.status === 'fulfilled' && result.value) {
        const { id, users_count } = result.value;
        realms = realms.map(r => r.id === id ? { ...r, users_count } : r);
        filteredRealms = filteredRealms.map(r => r.id === id ? { ...r, users_count } : r);
      }
    });
  }

  function formatTimeAgo(timestamp) {
    const now = Date.now();
    const date = new Date(timestamp * 1000);
    const seconds = Math.floor((now - date.getTime()) / 1000);
    
    if (seconds < 60) return 'just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
    if (seconds < 2592000) return `${Math.floor(seconds / 604800)}w ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function formatFullDate(timestamp) {
    return new Date(timestamp * 1000).toLocaleString('en-US', {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  }

  async function addRealm() {
    if (!newRealm.id.trim() || !newRealm.name.trim()) {
      error = 'Realm ID and Name are required';
      return;
    }

    try {
      addingRealm = true;
      error = null;
      const result = await backend.add_realm(newRealm.id, newRealm.name, newRealm.url, newRealm.logo);
      
      if (result.Ok) {
        newRealm = { id: '', name: '', url: '', logo: '' };
        showAddForm = false;
        await loadRealms();
      } else {
        error = result.Err;
      }
    } catch (err) {
      error = err.message || 'Failed to add realm';
    } finally {
      addingRealm = false;
    }
  }


  // formatDate kept for backwards compatibility
  function formatDate(timestamp) {
    return formatTimeAgo(timestamp);
  }

  function truncateId(id) {
    if (!id || id.length <= 16) return id;
    return `${id.slice(0, 8)}...${id.slice(-4)}`;
  }

  function ensureProtocol(url) {
    if (!url) return '';
    // If URL already has a protocol, return as-is
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url;
    }
    // Use http for localhost, https for production
    const isLocal = url.includes('localhost') || url.includes('127.0.0.1');
    return isLocal ? `http://${url}` : `https://${url}`;
  }


  function searchRealms() {
    if (!searchQuery.trim()) {
      filteredRealms = realms;
      return;
    }
    
    const query = searchQuery.toLowerCase();
    filteredRealms = realms.filter(realm => 
      realm.id.toLowerCase().includes(query) || 
      realm.name.toLowerCase().includes(query)
    );
  }

  $: searchQuery, searchRealms();
</script>

<svelte:head>
  <title>Realm Registry</title>
</svelte:head>

<div class="container">
  <header class="header">
    <div class="header-content">
      <img src="/images/logo_horizontal.svg" alt="Realms Logo" class="header-logo" />
    </div>
  </header>

  <div class="controls">
    <div class="search-section">
      <div class="search-wrapper">
        <svg class="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"></circle>
          <path d="m21 21-4.35-4.35"></path>
        </svg>
        <input
          type="text"
          placeholder="Search realms by name or ID..."
          bind:value={searchQuery}
          class="search-input"
        />
        {#if searchQuery}
          <button class="search-clear" on:click={() => searchQuery = ''}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"></path>
            </svg>
          </button>
        {/if}
      </div>
    </div>
    
    <button 
      class="btn btn-primary add-btn"
      on:click={() => showAddForm = !showAddForm}
    >
      {showAddForm ? '✕ Cancel' : '+ Add Realm'}
    </button>
  </div>

  {#if showAddForm}
    <div class="add-form">
      <h3>Add New Realm</h3>
      <div class="form-row">
        <input
          type="text"
          placeholder="Realm ID (required)"
          bind:value={newRealm.id}
          class="form-input"
        />
        <input
          type="text"
          placeholder="Realm Name (required)"
          bind:value={newRealm.name}
          class="form-input"
        />
        <input
          type="text"
          placeholder="Canister URL (optional)"
          bind:value={newRealm.url}
          class="form-input"
        />
        <input
          type="text"
          placeholder="Logo URL (optional)"
          bind:value={newRealm.logo}
          class="form-input"
        />
      </div>
      <div class="form-actions">
        <button 
          class="btn btn-primary"
          on:click={addRealm}
          disabled={addingRealm}
        >
          {addingRealm ? 'Adding...' : 'Add Realm'}
        </button>
      </div>
    </div>
  {/if}

  {#if error}
    <div class="error-banner">
      <span>❌ {error}</span>
      <button on:click={() => error = null}>✕</button>
    </div>
  {/if}

  <main class="main-content">
    {#if loading}
      <div class="loading-grid">
        {#each [1, 2, 3] as _}
          <div class="skeleton-card">
            <div class="skeleton-icon"></div>
            <div class="skeleton-title"></div>
            <div class="skeleton-text"></div>
            <div class="skeleton-text short"></div>
            <div class="skeleton-buttons">
              <div class="skeleton-btn"></div>
              <div class="skeleton-btn"></div>
            </div>
          </div>
        {/each}
      </div>
    {:else if filteredRealms.length === 0}
      <div class="empty-state">
        {#if searchQuery}
          <h2>🔍 No Results</h2>
          <p>No realms found matching "{searchQuery}"</p>
        {:else}
          <h2>📋 No Realms</h2>
          <p>No realms have been registered yet.</p>
          <button 
            class="btn btn-primary"
            on:click={() => showAddForm = true}
          >
            Add First Realm
          </button>
        {/if}
      </div>
    {:else}
      <div class="realms-grid">
        {#each filteredRealms as realm}
          <div class="realm-card">
            <div class="card-accent"></div>
            <div class="realm-header">
              <div class="realm-logo-container">
                {#if realm.logo}
                  <img src={realm.logo} alt="{realm.name} logo" class="realm-logo" />
                {:else}
                  <div class="realm-logo-fallback">
                    <span>{realm.name.charAt(0).toUpperCase()}</span>
                  </div>
                {/if}
              </div>
              <div class="user-badge" class:has-users={realm.users_count > 0}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                </svg>
                <span>{realm.users_count || 0}</span>
              </div>
            </div>
            
            <div class="realm-content">
              <h3 class="realm-name">{realm.name}</h3>
              
              <p class="realm-info" title="{formatFullDate(realm.created_at)}">
                <code>{realm.id}</code>
                <span class="info-separator">·</span>
                <span>{formatTimeAgo(realm.created_at)}</span>
              </p>
            </div>
            
            <div class="realm-actions">
              {#if realm.url}
                <button 
                  class="btn btn-dark btn-sm btn-full"
                  on:click={() => window.open(ensureProtocol(realm.url), '_blank')}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                    <polyline points="15 3 21 3 21 9"></polyline>
                    <line x1="10" y1="14" x2="21" y2="3"></line>
                  </svg>
                  Visit
                </button>
              {/if}
            </div>
          </div>
        {/each}
      </div>
      
      <div class="stats">
        <p>Showing {filteredRealms.length} of {realms.length} realms</p>
      </div>
    {/if}
  </main>
  
  <!-- Footer -->
  <footer class="footer">
    <!-- Built on Internet Computer section -->
    <div class="footer-ic">
      <a href="https://internetcomputer.org" target="_blank" rel="noopener noreferrer" class="ic-link">
        <img src="/images/internet-computer-icp-logo.svg" alt="Internet Computer Logo" width="24" height="24" class="ic-logo" />
        <span>Built on the Internet Computer</span>
      </a>
    </div>
    
    <!-- GitHub link -->
    <div class="footer-links">
      <a href="https://github.com/smart-social-contracts/realms" target="_blank" rel="noopener noreferrer" class="github-link">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
        </svg>
      </a>
    </div>
    
    <!-- Version info with dynamic data -->
    {#if (version && version !== 'VERSION_PLACEHOLDER') || (commitHash && commitHash !== 'COMMIT_HASH_PLACEHOLDER') || (commitDatetime && commitDatetime !== 'COMMIT_DATETIME_PLACEHOLDER')}
      <div class="footer-version">
        <span>
          Realm Registry {#if version && version !== 'VERSION_PLACEHOLDER'}{version}{/if}
          {#if commitHash && commitHash !== 'COMMIT_HASH_PLACEHOLDER'}({commitHash}){/if}
          {#if commitDatetime && commitDatetime !== 'COMMIT_DATETIME_PLACEHOLDER'} - {commitDatetime}{/if}
        </span>
      </div>
    {/if}
  </footer>
</div>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: 'Inter', ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif;
    background: #FAFAFA;
    min-height: 100vh;
    color: #171717;
  }

  .container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  .header {
    text-align: center;
    margin-bottom: 2rem;
    color: #171717;
  }

  .logo {
    height: 3rem;
    margin-bottom: 1rem;
  }

  .header-content {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
  }

  .header-logo {
    height: 120px;
    width: auto;
  }

  .header h1 {
    font-size: 2.5rem;
    margin: 0;
    font-weight: 700;
    color: #171717;
  }

  .subtitle {
    font-size: 1.2rem;
    margin: 1rem 0 0 0;
    color: #525252;
    font-weight: 400;
  }

  .controls {
    display: flex;
    gap: 1rem;
    margin-bottom: 2rem;
    align-items: center;
    flex-wrap: wrap;
  }

  .search-section {
    flex: 1;
    min-width: 300px;
  }

  .search-wrapper {
    position: relative;
    display: flex;
    align-items: center;
  }

  .search-icon {
    position: absolute;
    left: 1rem;
    color: #A3A3A3;
    pointer-events: none;
  }

  .search-input {
    width: 100%;
    padding: 1rem 2.5rem 1rem 3rem;
    font-size: 1rem;
    border: 1px solid #E5E5E5;
    border-radius: 0.75rem;
    background: #FFFFFF;
    color: #171717;
    font-family: inherit;
    transition: all 0.2s ease;
  }

  .search-input:focus {
    outline: none;
    border-color: #525252;
    box-shadow: 0 0 0 3px rgba(82, 82, 82, 0.1);
  }

  .search-input:focus + .search-icon,
  .search-wrapper:focus-within .search-icon {
    color: #525252;
  }

  .search-clear {
    position: absolute;
    right: 0.75rem;
    background: none;
    border: none;
    padding: 0.25rem;
    cursor: pointer;
    color: #A3A3A3;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;
  }

  .search-clear:hover {
    color: #525252;
    background: #F5F5F5;
  }

  .add-btn {
    white-space: nowrap;
  }

  .add-form {
    background: #FFFFFF;
    padding: 2rem;
    border-radius: 0.75rem;
    margin-bottom: 2rem;
    border: 1px solid #E5E5E5;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.12), 0 2px 4px -1px rgba(0, 0, 0, 0.08);
  }

  .add-form h3 {
    margin: 0 0 1rem 0;
    color: #171717;
    font-weight: 600;
  }

  .form-row {
    display: flex;
    gap: 1rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
  }

  .form-input {
    flex: 1;
    min-width: 200px;
    padding: 0.75rem;
    border: 1px solid #E5E5E5;
    border-radius: 0.375rem;
    font-size: 1rem;
    background: #FFFFFF;
    color: #171717;
    font-family: inherit;
  }

  .form-input:focus {
    outline: none;
    border-color: #525252;
    box-shadow: 0 0 0 3px rgba(82, 82, 82, 0.1);
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;
  }

  .error-banner {
    background: #FAFAFA;
    color: #737373;
    padding: 1rem;
    border-radius: 0.5rem;
    margin-bottom: 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border: 1px solid #D4D4D4;
  }

  .error-banner button {
    background: none;
    border: none;
    color: #737373;
    cursor: pointer;
    font-size: 1.2rem;
  }

  .main-content {
    flex: 1;
    background: #FFFFFF;
    border-radius: 0.75rem;
    padding: 2rem;
    border: 1px solid #E5E5E5;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.12), 0 2px 4px -1px rgba(0, 0, 0, 0.08);
  }

  .loading, .empty-state {
    text-align: center;
    padding: 3rem;
  }

  .loading-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1.5rem;
  }

  .skeleton-card {
    background: #FFFFFF;
    border-radius: 1rem;
    padding: 1.5rem;
    border: 1px solid #E5E5E5;
  }

  .skeleton-icon {
    width: 72px;
    height: 72px;
    border-radius: 1rem;
    background: linear-gradient(90deg, #F5F5F5 25%, #E5E5E5 50%, #F5F5F5 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    margin: 0 auto 1rem;
  }

  .skeleton-title {
    height: 24px;
    width: 60%;
    border-radius: 6px;
    background: linear-gradient(90deg, #F5F5F5 25%, #E5E5E5 50%, #F5F5F5 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    margin: 0 auto 0.75rem;
  }

  .skeleton-text {
    height: 16px;
    width: 80%;
    border-radius: 4px;
    background: linear-gradient(90deg, #F5F5F5 25%, #E5E5E5 50%, #F5F5F5 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    margin: 0 auto 0.5rem;
  }

  .skeleton-text.short {
    width: 50%;
  }

  .skeleton-buttons {
    display: flex;
    gap: 0.75rem;
    justify-content: center;
    margin-top: 1.5rem;
  }

  .skeleton-btn {
    height: 36px;
    width: 100px;
    border-radius: 6px;
    background: linear-gradient(90deg, #F5F5F5 25%, #E5E5E5 50%, #F5F5F5 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
  }

  @keyframes shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 4px solid #F5F5F5;
    border-top: 4px solid #525252;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 1rem;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  .realms-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
  }

  .realm-card {
    background: #FFFFFF;
    border-radius: 1rem;
    padding: 0;
    border: 1px solid #E5E5E5;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.08);
    position: relative;
    overflow: hidden;
    transition: all 0.2s ease;
  }

  .realm-card:hover {
    border-color: #D4D4D4;
    box-shadow: 0 8px 25px -5px rgba(0, 0, 0, 0.1), 0 4px 10px -5px rgba(0, 0, 0, 0.04);
    transform: translateY(-2px);
  }

  .card-accent {
    height: 4px;
    background: linear-gradient(90deg, #404040 0%, #737373 100%);
  }

  .realm-header {
    padding: 1.5rem 1.5rem 0;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }

  .realm-logo-container {
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .realm-logo {
    width: 72px;
    height: 72px;
    object-fit: contain;
    border-radius: 1rem;
    background: #F5F5F5;
    padding: 0.5rem;
  }

  .realm-logo-fallback {
    width: 72px;
    height: 72px;
    border-radius: 1rem;
    background: linear-gradient(135deg, #525252 0%, #737373 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #FFFFFF;
    font-size: 1.75rem;
    font-weight: 600;
  }

  .user-badge {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.35rem 0.75rem;
    border-radius: 2rem;
    background: #F5F5F5;
    color: #737373;
    font-size: 0.8rem;
    font-weight: 500;
  }

  .user-badge.has-users {
    background: #DCFCE7;
    color: #166534;
  }

  .user-badge svg {
    opacity: 0.8;
  }

  .realm-content {
    padding: 1rem 1.5rem;
    text-align: center;
  }

  .realm-name {
    margin: 0 0 0.5rem;
    color: #171717;
    font-size: 1.35rem;
    font-weight: 600;
  }

  .realm-info {
    margin: 0;
    font-size: 0.8rem;
    color: #737373;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .realm-info code {
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 0.75rem;
    color: #525252;
  }

  .info-separator {
    color: #A3A3A3;
  }

  .realm-id {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: #F5F5F5;
    padding: 0.35rem 0.75rem;
    border-radius: 0.5rem;
    margin-bottom: 1rem;
  }

  .realm-id code {
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 0.75rem;
    color: #737373;
  }

  .copy-id-btn {
    background: none;
    border: none;
    padding: 0.2rem;
    cursor: pointer;
    color: #A3A3A3;
    border-radius: 4px;
    display: flex;
    align-items: center;
    transition: all 0.15s ease;
  }

  .copy-id-btn:hover {
    color: #525252;
    background: #E5E5E5;
  }

  .realm-meta {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    text-align: left;
  }

  .realm-meta p {
    margin: 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    color: #525252;
  }

  .meta-label {
    font-weight: 500;
    color: #737373;
    font-size: 0.8rem;
  }

  .realm-meta svg {
    color: #A3A3A3;
    flex-shrink: 0;
  }

  .realm-meta code {
    font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 0.8rem;
    color: #525252;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .health-indicator {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    font-size: 0.8rem;
    padding: 0.25rem 0.5rem;
    border-radius: 12px;
    background: rgba(255,255,255,0.8);
    border: 1px solid #e1e5e9;
  }

  .health-icon {
    font-size: 0.9rem;
  }

  .health-label {
    font-weight: 500;
    color: #495057;
  }

  .realm-id {
    background: #e9ecef;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-family: monospace;
    font-size: 0.875rem;
    color: #6c757d;
  }

  .realm-details {
    margin-bottom: 1.5rem;
  }

  .realm-details p {
    margin: 0.5rem 0;
    font-size: 0.9rem;
  }

  .realm-url code {
    background: #f8f9fa;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
  }

  .realm-actions {
    display: flex;
    gap: 0.75rem;
    padding: 1rem 1.5rem 1.5rem;
    border-top: 1px solid #F5F5F5;
  }

  .btn {
    padding: 0.65rem 1.25rem;
    border: 1px solid transparent;
    border-radius: 0.5rem;
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.15s ease-in-out;
    font-weight: 500;
    font-family: inherit;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
  }

  .btn-sm {
    padding: 0.5rem 1rem;
    font-size: 0.8rem;
    flex: 1;
  }

  .btn-primary {
    background: #171717;
    color: #FFFFFF;
    border-color: #171717;
  }

  .btn-primary:hover {
    background: #262626;
    border-color: #262626;
    transform: translateY(-1px);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.12), 0 2px 4px -1px rgba(0, 0, 0, 0.08);
  }

  .btn-accent {
    background: #2563EB;
    color: #FFFFFF;
    border-color: #2563EB;
  }

  .btn-accent:hover {
    background: #1D4ED8;
    border-color: #1D4ED8;
    transform: translateY(-1px);
    box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.25), 0 2px 4px -1px rgba(37, 99, 235, 0.15);
  }

  .btn-dark {
    background: #171717;
    color: #FFFFFF;
    border-color: #171717;
  }

  .btn-dark:hover {
    background: #404040;
    border-color: #404040;
    transform: translateY(-1px);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2), 0 2px 4px -1px rgba(0, 0, 0, 0.1);
  }

  .btn-full {
    width: 100%;
    justify-content: center;
  }

  .btn-ghost {
    background: transparent;
    color: #525252;
    border-color: #E5E5E5;
  }

  .btn-ghost:hover {
    background: #F5F5F5;
    border-color: #D4D4D4;
    color: #171717;
  }

  .btn-secondary {
    background: #FFFFFF;
    color: #171717;
    border-color: #E5E5E5;
  }

  .btn-secondary:hover {
    background: #F5F5F5;
    border-color: #D4D4D4;
    transform: translateY(-1px);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.12), 0 2px 4px -1px rgba(0, 0, 0, 0.08);
  }

  .btn-danger {
    background: #DC2626;
    color: #FFFFFF;
    border-color: #DC2626;
  }

  .btn-danger:hover {
    background: #B91C1C;
    border-color: #B91C1C;
    transform: translateY(-1px);
    box-shadow: 0 4px 6px -1px rgba(220, 38, 38, 0.12), 0 2px 4px -1px rgba(220, 38, 38, 0.08);
  }

  .drawer-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.5);
    z-index: 1000;
    display: flex;
    justify-content: flex-end;
    animation: fadeIn 0.3s ease-out;
  }

  .drawer {
    width: 500px;
    height: 100%;
    background: #FFFFFF;
    border-left: 1px solid #E5E5E5;
    box-shadow: -4px 0 20px rgba(0, 0, 0, 0.15);
    transform: translateX(100%);
    transition: transform 0.3s ease;
    overflow-y: auto;
  }


  .drawer-header {
    padding: 2rem;
    border-bottom: 1px solid #E5E5E5;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .drawer-header h2 {
    margin: 0;
    color: #171717;
    font-weight: 600;
  }

  .close-btn {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: #6c757d;
    padding: 0.5rem;
    border-radius: 4px;
    transition: background-color 0.2s;
  }

  .close-btn:hover {
    background: rgba(0,0,0,0.1);
  }

  .drawer-content {
    padding: 2rem;
  }

  .drawer-content label {
    font-weight: 600;
    color: #171717;
    display: block;
    margin-bottom: 0.5rem;
    font-size: 0.875rem;
  }

  .drawer-content p {
    margin: 0 0 1.5rem 0;
    color: #525252;
    word-break: break-all;
    font-size: 0.875rem;
  }

  .status-section, .sharing-section, .actions-section {
    margin-bottom: 2rem;
  }

  .status-section h3, .sharing-section h3 {
    margin: 0 0 1rem 0;
    color: #2c3e50;
    font-size: 1.1rem;
  }

  .status-card, .sharing-card {
    background: #f8f9fa;
    border: 1px solid #e1e5e9;
    border-radius: 8px;
    padding: 1rem;
  }

  .status-indicator {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 1rem;
    padding: 0.75rem;
    background: white;
    border-radius: 6px;
    border: 1px solid #dee2e6;
  }

  .status-icon {
    font-size: 1.2rem;
  }

  .status-text {
    font-weight: 600;
    color: #495057;
  }

  .status-details p {
    margin: 0.5rem 0;
    font-size: 0.9rem;
    color: #6c757d;
  }

  .public-link {
    margin-bottom: 1.5rem;
  }

  .public-link label, .qr-code label {
    display: block;
    margin-bottom: 0.5rem;
    font-weight: 600;
    color: #495057;
    font-size: 0.9rem;
  }

  .link-input {
    display: flex;
    gap: 0.5rem;
  }

  .link-field {
    flex: 1;
    padding: 0.5rem;
    border: 1px solid #ced4da;
    border-radius: 4px;
    font-size: 0.85rem;
    font-family: monospace;
    background: white;
  }

  .qr-container {
    text-align: center;
    padding: 1rem;
    background: white;
    border-radius: 6px;
    border: 1px solid #dee2e6;
  }

  .qr-image {
    max-width: 150px;
    height: auto;
    border-radius: 4px;
  }

  .actions-section {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes slideIn {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
  }

  .stats {
    text-align: center;
    color: #6c757d;
    font-size: 0.9rem;
    padding-top: 1rem;
    border-top: 1px solid #e1e5e9;
  }

  /* Footer Styles */
  .footer {
    margin-top: 3rem;
    padding: 1.5rem;
    border-top: 1px solid #E5E5E5;
    background: #FFFFFF;
    border-radius: 0.75rem;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.12), 0 2px 4px -1px rgba(0, 0, 0, 0.08);
  }

  .footer-ic {
    display: flex;
    justify-content: center;
    margin-bottom: 0.75rem;
  }

  .ic-link {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: #737373;
    text-decoration: none;
    transition: color 0.15s ease-in-out;
    font-size: 0.875rem;
  }

  .ic-link:hover {
    color: #171717;
  }

  .ic-logo {
    width: 24px;
    height: 24px;
  }

  .footer-links {
    display: flex;
    justify-content: center;
    margin-top: 1rem;
  }

  .github-link {
    color: #737373;
    transition: all 0.15s ease-in-out;
    padding: 0.5rem;
    border-radius: 6px;
    text-decoration: none;
  }

  .github-link:hover {
    color: #171717;
    background: rgba(0,0,0,0.05);
  }

  .footer-version {
    text-align: center;
    margin-top: 0.75rem;
  }

  .footer-version span {
    font-size: 0.75rem;
    color: #A3A3A3;
  }

  @media (max-width: 768px) {
    .container {
      padding: 1rem;
    }

    .header {
      margin-bottom: 1rem;
    }

    .header h1 {
      font-size: 2rem;
    }

    .header-content {
      flex-direction: column;
    }

    .header-logo {
      height: 50px;
    }

    .controls {
      flex-direction: column;
      align-items: stretch;
      margin-bottom: 1rem;
    }

    .main-content {
      padding: 1rem;
    }

    .form-row {
      flex-direction: column;
    }

    .realms-grid {
      grid-template-columns: 1fr;
      gap: 1rem;
    }

    .realm-header {
      padding: 1rem 1rem 0;
    }

    .realm-logo, .realm-logo-fallback {
      width: 56px;
      height: 56px;
    }

    .realm-content {
      padding: 0.75rem 1rem;
    }

    .realm-name {
      font-size: 1.1rem;
    }

    .realm-actions {
      padding: 0.75rem 1rem 1rem;
    }

    .card-accent {
      height: 3px;
    }
  }
</style>
