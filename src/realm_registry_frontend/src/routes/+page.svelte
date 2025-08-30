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
          <div class="realm-card">
            <div class="realm-header">
              <h3 class="realm-name">{realm.name}</h3>
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
            
            <div class="realm-actions">
              {#if realm.url}
                <button 
                  class="btn btn-primary"
                  on:click={() => window.open(`https://${realm.url}`, '_blank')}
                >
                  Visit Realm
                </button>
              {/if}
              <button 
                class="btn btn-danger"
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
    border-radius: 8px;
    padding: 1.5rem;
    background: #fafbfc;
    transition: transform 0.2s, box-shadow 0.2s;
  }

  .realm-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  }

  .realm-header {
    margin-bottom: 1rem;
  }

  .realm-name {
    margin: 0 0 0.5rem 0;
    color: #2c3e50;
    font-size: 1.25rem;
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
