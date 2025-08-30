<script>
  import { onMount } from 'svelte';
  import { backend } from "$lib/canisters";

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

  async function removeRealm(realmId) {
    if (!confirm(`Are you sure you want to remove realm "${realmId}"?`)) {
      return;
    }

    try {
      const result = await backend.remove_realm(realmId);
      if (result.Ok) {
        await loadRealms();
      } else {
        error = result.Err;
      }
    } catch (err) {
      error = err.message || 'Failed to remove realm';
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

  function getRealmHealth(realm) {
    // Simulate health status based on realm properties
    if (!realm.url) return { status: 'offline', icon: '🔴', label: 'Offline' };
    
    // Simple heuristic: newer realms are healthier
    const daysSinceCreation = (Date.now() / 1000 - realm.created_at) / (24 * 60 * 60);
    if (daysSinceCreation < 7) return { status: 'healthy', icon: '🟢', label: 'Healthy' };
    if (daysSinceCreation < 30) return { status: 'degraded', icon: '🟡', label: 'Degraded' };
    return { status: 'offline', icon: '🔴', label: 'Offline' };
  }

  function openRealmDetails(realm) {
    selectedRealm = realm;
    showDrawer = true;
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

  function generateQRCode(text) {
    // Simple QR code using qr-server.com API
    return `https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(text)}`;
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
    <h1>🌍 Realm Registry</h1>
    <p class="subtitle">Discover and explore Realm instances on the Internet Computer</p>
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
          <div class="realm-card" on:click={() => openRealmDetails(realm)}>
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
            
            <div class="realm-actions" on:click|stopPropagation>
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
              <button 
                class="btn btn-danger btn-sm"
                on:click={() => removeRealm(realm.id)}
              >
                Remove
              </button>
            </div>
          </div>
        {/each}
      </div>
      
      <div class="stats">
        <p>Showing {filteredRealms.length} of {realms.length} realms</p>
      </div>
    {/if}
  </main>
</div>

<!-- Realm Details Drawer -->
{#if showDrawer && selectedRealm}
  <div class="drawer-overlay" on:click={closeDrawer}>
    <div class="drawer" on:click|stopPropagation>
      <div class="drawer-header">
        <h2>{selectedRealm.name}</h2>
        <button class="close-btn" on:click={closeDrawer}>✕</button>
      </div>
      
      <div class="drawer-content">
        <div class="status-section">
          <h3>Status</h3>
          <div class="status-card">
            <div class="status-indicator">
              <span class="status-icon">{getRealmHealth(selectedRealm).icon}</span>
              <span class="status-text">{getRealmHealth(selectedRealm).label}</span>
            </div>
            <div class="status-details">
              <p><strong>Realm ID:</strong> {selectedRealm.id}</p>
              <p><strong>Created:</strong> {formatDate(selectedRealm.created_at)}</p>
              {#if selectedRealm.url}
                <p><strong>URL:</strong> <code>{selectedRealm.url}</code></p>
              {/if}
            </div>
          </div>
        </div>
        
        <div class="sharing-section">
          <h3>Share Realm</h3>
          <div class="sharing-card">
            <div class="public-link">
              <label>Public Link:</label>
              <div class="link-input">
                <input 
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
              <label>QR Code:</label>
              <div class="qr-container">
                <img 
                  src={generateQRCode(getPublicLink(selectedRealm))} 
                  alt="QR Code for {selectedRealm.name}"
                  class="qr-image"
                />
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
          <button 
            class="btn btn-danger"
            on:click={() => { removeRealm(selectedRealm.id); closeDrawer(); }}
          >
            🗑️ Remove Realm
          </button>
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
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
    color: white;
  }

  .header h1 {
    font-size: 3rem;
    margin: 0;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
  }

  .subtitle {
    font-size: 1.2rem;
    margin: 1rem 0 0 0;
    opacity: 0.9;
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
    border: none;
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  }

  .search-input:focus {
    outline: none;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
  }

  .add-btn {
    white-space: nowrap;
  }

  .add-form {
    background: white;
    padding: 2rem;
    border-radius: 12px;
    margin-bottom: 2rem;
    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
  }

  .add-form h3 {
    margin: 0 0 1rem 0;
    color: #2c3e50;
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
    border: 1px solid #ddd;
    border-radius: 6px;
    font-size: 1rem;
  }

  .form-input:focus {
    outline: none;
    border-color: #667eea;
    box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;
  }

  .error-banner {
    background: #fee;
    color: #c33;
    padding: 1rem;
    border-radius: 8px;
    margin-bottom: 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border: 1px solid #fcc;
  }

  .error-banner button {
    background: none;
    border: none;
    color: #c33;
    cursor: pointer;
    font-size: 1.2rem;
  }

  .main-content {
    flex: 1;
    background: white;
    border-radius: 12px;
    padding: 2rem;
    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
  }

  .loading, .empty-state {
    text-align: center;
    padding: 3rem;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 4px solid #f3f3f3;
    border-top: 4px solid #667eea;
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
    border: 1px solid #e1e5e9;
    border-radius: 12px;
    padding: 1.5rem;
    background: #fafbfc;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    cursor: pointer;
    position: relative;
    overflow: hidden;
  }

  .realm-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
    transition: left 0.5s;
  }

  .realm-card:hover {
    transform: translateY(-8px) scale(1.02);
    box-shadow: 0 20px 40px rgba(0,0,0,0.15);
    border-color: #667eea;
  }

  .realm-card:hover::before {
    left: 100%;
  }

  .realm-card:active {
    transform: translateY(-4px) scale(1.01);
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
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.875rem;
    transition: background-color 0.2s;
    text-decoration: none;
    display: inline-block;
  }

  .btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .btn-primary {
    background: #667eea;
    color: white;
  }

  .btn-primary:hover:not(:disabled) {
    background: #5a6fd8;
  }

  .btn-danger {
    background: #dc3545;
    color: white;
  }

  .btn-danger:hover {
    background: #c82333;
  }

  .btn-secondary {
    background: #6c757d;
    color: white;
  }

  .btn-secondary:hover {
    background: #5a6268;
  }

  .btn-sm {
    padding: 0.375rem 0.75rem;
    font-size: 0.8rem;
  }

  /* Drawer Styles */
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
    width: 400px;
    max-width: 90vw;
    background: white;
    height: 100vh;
    overflow-y: auto;
    box-shadow: -4px 0 20px rgba(0,0,0,0.1);
    animation: slideIn 0.3s ease-out;
  }

  .drawer-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1.5rem;
    border-bottom: 1px solid #e1e5e9;
    background: #f8f9fa;
  }

  .drawer-header h2 {
    margin: 0;
    color: #2c3e50;
    font-size: 1.5rem;
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
    padding: 1.5rem;
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

  @media (max-width: 768px) {
    .container {
      padding: 1rem;
    }

    .header h1 {
      font-size: 2rem;
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
