<script>
  import { onMount } from 'svelte';
  import { backend } from "$lib/canisters";
  import QRCode from 'qrcode';

  let realms = [];
  let loading = true;
  let error = null;
  let searchQuery = '';
  let filteredRealms = [];
  let showAddForm = false;
  let newRealm = { id: '', name: '', url: '' };
  let addingRealm = false;
  let selectedRealm = null;
  let showDrawer = false;
  let copiedLink = null;
  let qrCodeDataUrl = '';

  onMount(async () => {
    await loadRealms();
  });

  async function loadRealms() {
    try {
      loading = true;
      error = null;
      const response = await backend.list_realms();
      realms = response || [];
      filteredRealms = realms;
      loading = false;
    } catch (err) {
      error = err.message || 'Failed to load realms';
      loading = false;
    }
  }

  async function addRealm() {
    if (!newRealm.id.trim() || !newRealm.name.trim()) {
      error = 'Realm ID and Name are required';
      return;
    }

    try {
      addingRealm = true;
      error = null;
      const result = await backend.add_realm(newRealm.id, newRealm.name, newRealm.url);
      
      if (result.Ok) {
        newRealm = { id: '', name: '', url: '' };
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


  function formatDate(timestamp) {
    return new Date(timestamp * 1000).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  async function getRealmStatus(realm) {
    try {
      if (!realm.url) {
        return {
          status: 'unknown',
          icon: '❓',
          label: 'Status unavailable',
          details: 'No URL configured for this realm'
        };
      }

      const statusUrl = `https://${realm.url}/status`;
      const response = await fetch(statusUrl);
      
      if (response.ok) {
        const statusData = await response.json();
        return {
          status: 'healthy',
          icon: '✅',
          label: 'Healthy',
          details: statusData
        };
      } else {
        return {
          status: 'error',
          icon: '❌',
          label: 'Error',
          details: `HTTP ${response.status}: ${response.statusText}`
        };
      }
    } catch (error) {
      return {
        status: 'error',
        icon: '❌',
        label: 'Error',
        details: error.message
      };
    }
  }

  async function openRealmDetails(realm) {
    selectedRealm = realm;
    selectedRealm.statusInfo = await getRealmStatus(realm);
    showDrawer = true;
    // Generate QR code when drawer opens
    qrCodeDataUrl = await generateQRCode(getPublicLink(realm));
  }

  function closeDrawer() {
    showDrawer = false;
    selectedRealm = null;
  }

  function getPublicLink(realm) {
    return realm.url ? `https://${realm.url}` : `${window.location.origin}/realm/${realm.id}`;
  }

  async function copyLink(realm) {
    const link = getPublicLink(realm);
    try {
      await navigator.clipboard.writeText(link);
      copiedLink = realm.id;
      setTimeout(() => copiedLink = null, 2000);
    } catch (err) {
      console.error('Failed to copy link:', err);
    }
  }

  async function generateQRCode(text) {
    try {
      const dataUrl = await QRCode.toDataURL(text, {
        width: 200,
        margin: 2,
        color: {
          dark: '#2c3e50',
          light: '#ffffff'
        }
      });
      return dataUrl;
    } catch (err) {
      console.error('Failed to generate QR code:', err);
      return '';
    }
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
      <div class="header-text">
        <h1>🌍 Realms Registry</h1>
        <p class="subtitle">Discover and explore Realm instances on the Internet Computer</p>
      </div>
    </div>
  </header>

  <div class="controls">
    <div class="search-section">
      <input
        type="text"
        placeholder="Search realms by name or ID..."
        bind:value={searchQuery}
        class="search-input"
      />
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
      <div class="loading">
        <div class="spinner"></div>
        <p>Loading realms...</p>
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
          <button class="realm-card" on:click={() => openRealmDetails(realm)} type="button">
            <div class="realm-header">
              <div class="realm-title">
                <h3 class="realm-name">{realm.name}</h3>
                <div class="health-indicator" title={getRealmHealth(realm).label}>
                  <span class="health-icon">{getRealmHealth(realm).icon}</span>
                  <span class="health-label">{getRealmHealth(realm).label}</span>
                </div>
              </div>
              <span class="realm-id">{realm.id}</span>
            </div>
            
            <div class="realm-details">
              {#if realm.url}
                <p class="realm-url">
                  <strong>URL:</strong> 
                  <code>{realm.url}</code>
                </p>
              {/if}
              
              <p class="realm-date">
                <strong>Created:</strong> {formatDate(realm.created_at)}
              </p>
            </div>
            
            <div class="realm-actions" on:click|stopPropagation on:keydown|stopPropagation role="group" aria-label="Realm actions">
              <button 
                class="btn btn-secondary btn-sm"
                on:click={() => copyLink(realm)}
                title="Copy public link"
              >
                {copiedLink === realm.id ? '✓ Copied!' : '🔗 Copy Link'}
              </button>
              {#if realm.url}
                <button 
                  class="btn btn-primary btn-sm"
                  on:click={() => window.open(`https://${realm.url}`, '_blank')}
                >
                  Visit
                </button>
              {/if}
            </div>
          </button>
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
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" class="ic-logo">
          <circle cx="12" cy="12" r="10" fill="url(#gradient)" />
          <path d="M8 12h8M12 8v8" stroke="white" stroke-width="2" stroke-linecap="round" />
          <defs>
            <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" style="stop-color:#667eea" />
              <stop offset="100%" style="stop-color:#764ba2" />
            </linearGradient>
          </defs>
        </svg>
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
    
    <!-- Version info -->
    <div class="footer-version">
      <span>Realm Registry v1.0</span>
    </div>
  </footer>
</div>

<!-- Realm Details Drawer -->
{#if showDrawer && selectedRealm}
  <div class="drawer-overlay" on:click={closeDrawer} on:keydown={(e) => e.key === 'Escape' && closeDrawer()} role="dialog" aria-modal="true">
    <div class="drawer" on:click|stopPropagation on:keydown|stopPropagation role="document">
      <div class="drawer-header">
        <h2>{selectedRealm.name}</h2>
        <button class="close-btn" on:click={closeDrawer}>✕</button>
      </div>
      
      <div class="drawer-content">
        <div class="status-section">
          <h3>Status</h3>
          <div class="status-card">
            <div class="status-indicator">
              <span class="status-icon">{selectedRealm.statusInfo?.icon || '🔄'}</span>
              <span class="status-text">{selectedRealm.statusInfo?.label || 'Loading...'}</span>
            </div>
            <div class="status-details">
              <p><strong>Realm ID:</strong> {selectedRealm.id}</p>
              <p><strong>Created:</strong> {formatDate(selectedRealm.created_at)}</p>
              {#if selectedRealm.url}
                <p><strong>URL:</strong> <code>{selectedRealm.url}</code></p>
              {/if}
              <p><strong>Last Check:</strong> {new Date().toLocaleString()}</p>
              {#if selectedRealm.statusInfo?.details && typeof selectedRealm.statusInfo.details === 'object'}
                <p><strong>Version:</strong> {selectedRealm.statusInfo.details.version || 'Unknown'}</p>
                <p><strong>Users:</strong> {selectedRealm.statusInfo.details.users_count || 0}</p>
                <p><strong>Organizations:</strong> {selectedRealm.statusInfo.details.organizations_count || 0}</p>
              {:else if selectedRealm.statusInfo?.details}
                <p><strong>Details:</strong> {selectedRealm.statusInfo.details}</p>
              {/if}
            </div>
          </div>
        </div>
        
        <div class="sharing-section">
          <h3>Share Realm</h3>
          <div class="sharing-card">
            <div class="public-link">
              <label for="public-link-input">Public Link:</label>
              <div class="link-input">
                <input 
                  id="public-link-input"
                  type="text" 
                  value={getPublicLink(selectedRealm)} 
                  readonly 
                  class="link-field"
                />
                <button 
                  class="btn btn-primary btn-sm"
                  on:click={() => copyLink(selectedRealm)}
                >
                  {copiedLink === selectedRealm.id ? '✓' : 'Copy'}
                </button>
              </div>
            </div>
            
            <div class="qr-code">
              <label for="qr-code-container">QR Code:</label>
              <div id="qr-code-container" class="qr-container">
                {#if qrCodeDataUrl}
                  <img 
                    src={qrCodeDataUrl} 
                    alt="QR Code for {selectedRealm.name}"
                    class="qr-image"
                  />
                {:else}
                  <div class="qr-loading">Generating QR code...</div>
                {/if}
              </div>
            </div>
          </div>
        </div>
        
        <div class="actions-section">
          {#if selectedRealm.url}
            <button 
              class="btn btn-primary"
              on:click={() => window.open(`https://${selectedRealm.url}`, '_blank')}
            >
              🌐 Visit Realm
            </button>
          {/if}
        </div>
      </div>
    </div>
  </div>
{/if}

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
    height: 60px;
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

  .search-input {
    width: 100%;
    padding: 1rem;
    font-size: 1rem;
    border: 1px solid #E5E5E5;
    border-radius: 0.5rem;
    background: #FFFFFF;
    color: #171717;
    font-family: inherit;
  }

  .search-input:focus {
    outline: none;
    border-color: #525252;
    box-shadow: 0 0 0 3px rgba(82, 82, 82, 0.1);
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
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
  }

  .realm-card {
    background: #FFFFFF;
    border-radius: 0.75rem;
    padding: 1.5rem;
    border: 1px solid #E5E5E5;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
    transition: all 0.15s ease-in-out;
    cursor: pointer;
    position: relative;
    overflow: hidden;
    width: 100%;
    text-align: left;
    font-family: inherit;
    font-size: inherit;
  }

  .realm-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(23, 23, 23, 0.05), transparent);
    transition: left 0.3s ease-in-out;
  }

  .realm-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    border-color: #D4D4D4;
  }

  .realm-card:hover::before {
    left: 100%;
  }

  .realm-header {
    margin-bottom: 1rem;
  }

  .realm-title {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }

  .realm-name {
    margin: 0;
    color: #2c3e50;
    font-size: 1.25rem;
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
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .btn {
    padding: 0.75rem 1.5rem;
    border: 1px solid transparent;
    border-radius: 0.375rem;
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.15s ease-in-out;
    font-weight: 500;
    font-family: inherit;
    display: inline-flex;
    align-items: center;
    justify-content: center;
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
    padding: 2rem 0;
    border-top: 1px solid #E5E5E5;
    text-align: center;
    color: #737373;
    font-size: 0.875rem;
    background: #FAFAFA;
  }


  .footer-links {
    display: flex;
    justify-content: center;
  }

  .github-link {
    color: #6c757d;
    transition: color 0.2s;
    padding: 0.5rem;
    border-radius: 6px;
  }

  .github-link:hover {
    color: #2c3e50;
    background: rgba(0,0,0,0.05);
  }

  .footer-version {
    text-align: center;
  }

  .footer-version span {
    font-size: 0.8rem;
    color: #9ca3af;
  }

  @media (max-width: 768px) {
    .container {
      padding: 1rem;
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

    .header-content {
      flex-direction: column;
    }

    .header-logo {
      height: 50px;
    }

    .controls {
      flex-direction: column;
      align-items: stretch;
    }

    .form-row {
      flex-direction: column;
    }

    .realms-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
