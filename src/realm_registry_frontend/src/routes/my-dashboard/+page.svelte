<script>
  import { onMount } from 'svelte';
  import { browser } from '$app/environment';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { _, locale } from 'svelte-i18n';
  import { CONFIG } from '$lib/config.js';

  let userPrincipal = null;
  let loading = true;
  let activeTab = 'credits';
  
  // Read tab from URL parameter (?tab=realms or ?tab=credits)
  $: if (browser && $page.url.searchParams.get('tab')) {
    const tabParam = $page.url.searchParams.get('tab');
    if (tabParam === 'realms' || tabParam === 'credits') {
      activeTab = tabParam;
    }
  }
  
  // Credits data
  let balance = 0;
  let purchases = [];
  let loadingCredits = true;
  
  // Realms data
  let createdRealms = [];
  let joinedRealms = [];
  let loadingRealms = true;

  // Deployments data
  let deployments = [];
  let loadingDeployments = true;
  let deploymentPollInterval = null;
  
  // Canister management service URL
  const CANISTER_MGMT_URL = CONFIG.canister_management_url || 'https://canister-management.realmsgos.dev';

  // Top-up state
  let topUpAmount = 10;
  let topUpLoading = false;
  let topUpError = null;

  // Voucher state
  let voucherCode = '';
  let voucherLoading = false;
  let voucherError = null;
  let voucherSuccess = null;
  let redeemedVouchers = [];

  // Billing service URL - should be configured per environment
  const BILLING_SERVICE_URL = CONFIG.billing_service_url || 'http://localhost:8001';

  onMount(async () => {
    if (browser) {
      // Check if user is authenticated
      const { isAuthenticated, getPrincipal } = await import('$lib/auth.js');
      const authenticated = await isAuthenticated();
      
      if (!authenticated) {
        // Redirect to home if not logged in
        goto('/');
        return;
      }
      
      userPrincipal = await getPrincipal();
      loading = false;
      
      // Load deployments first (fast API call) - don't wait for slow canister calls
      loadDeployments();
      
      // Load other data in parallel (canister calls can be slow)
      loadCredits();
      loadRealms();
      loadVouchers();
      
      // Start polling for deployment status updates
      startDeploymentPolling();
    }
  });
  
  import { onDestroy } from 'svelte';
  
  onDestroy(() => {
    // Clean up polling interval
    if (deploymentPollInterval) {
      clearInterval(deploymentPollInterval);
    }
  });

  async function loadCredits() {
    loadingCredits = true;
    try {
      const { backend } = await import('$lib/canisters.js');
      const result = await backend.get_credits(userPrincipal.toText());
      
      if ('Ok' in result) {
        balance = Number(result.Ok.balance);
        purchases = [];
      } else {
        console.error('Failed to get credits:', result.Err);
        balance = 0;
        purchases = [];
      }
    } catch (err) {
      console.error('Failed to load credits:', err);
      balance = 0;
      purchases = [];
    } finally {
      loadingCredits = false;
    }
  }

  async function loadRealms() {
    if (!userPrincipal) return;
    loadingRealms = true;
    try {
      const { backend } = await import('$lib/canisters.js');
      // Try to get the user's realm (realm ID = user's principal)
      const result = await backend.get_realm(userPrincipal.toText());
      if ('Ok' in result) {
        createdRealms = [{
          id: result.Ok.id,
          name: result.Ok.name,
          url: result.Ok.url
        }];
      } else {
        createdRealms = [];
      }
      // TODO: Implement joined realms when membership feature is added
      joinedRealms = [];
    } catch (err) {
      console.error('Failed to load realms:', err);
      createdRealms = [];
      joinedRealms = [];
    } finally {
      loadingRealms = false;
    }
  }

  async function loadDeployments() {
    if (!userPrincipal) return;
    loadingDeployments = true;
    try {
      const response = await fetch(`${CANISTER_MGMT_URL}/api/deploy?principal_id=${userPrincipal.toText()}`);
      if (response.ok) {
        deployments = await response.json();
        // Sort by created_at descending
        deployments.sort((a, b) => b.created_at - a.created_at);
      }
    } catch (err) {
      console.error('Failed to load deployments:', err);
      deployments = [];
    } finally {
      loadingDeployments = false;
    }
  }

  function startDeploymentPolling() {
    // Poll every 10 seconds for deployment status updates
    deploymentPollInterval = setInterval(async () => {
      // Only poll if there are active deployments
      const hasActiveDeployments = deployments.some(d => 
        d.status === 'pending' || d.status === 'in_progress'
      );
      
      if (hasActiveDeployments) {
        await loadDeployments();
        // Refresh credits if a deployment completed
        const justCompleted = deployments.some(d => d.status === 'completed');
        if (justCompleted) {
          await loadCredits();
        }
      }
    }, 10000);
  }

  function getDeploymentStatusColor(status) {
    switch (status) {
      case 'completed': return '#22c55e';
      case 'failed': return '#ef4444';
      case 'in_progress': return '#3b82f6';
      case 'pending': return '#f59e0b';
      default: return '#6b7280';
    }
  }

  function getDeploymentStatusLabel(status) {
    switch (status) {
      case 'completed': return 'Completed';
      case 'failed': return 'Failed';
      case 'in_progress': return 'Deploying...';
      case 'pending': return 'Pending';
      default: return status;
    }
  }

  function formatDate(dateValue) {
    // Handle both unix timestamps and ISO date strings
    if (typeof dateValue === 'number') {
      return new Date(dateValue * 1000).toLocaleString();
    }
    return new Date(dateValue).toLocaleDateString();
  }

  async function loadVouchers() {
    if (!userPrincipal) return;
    try {
      const response = await fetch(`${BILLING_SERVICE_URL}/voucher/redemptions/${userPrincipal.toText()}`);
      if (response.ok) {
        redeemedVouchers = await response.json();
      }
    } catch (err) {
      console.error('Failed to load vouchers:', err);
    }
  }

  async function handleRedeemVoucher() {
    if (!userPrincipal || !voucherCode.trim()) return;
    
    voucherLoading = true;
    voucherError = null;
    voucherSuccess = null;
    
    try {
      const response = await fetch(`${BILLING_SERVICE_URL}/voucher/redeem`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          principal_id: userPrincipal.toText(),
          code: voucherCode.trim(),
        }),
      });
      
      const data = await response.json();
      
      if (!response.ok || !data.success) {
        voucherError = data.message || data.detail || 'Failed to redeem voucher';
        return;
      }
      
      voucherSuccess = data.message;
      voucherCode = '';
      
      // Reload credits and vouchers
      await Promise.all([loadCredits(), loadVouchers()]);
      
    } catch (err) {
      console.error('Voucher redemption failed:', err);
      voucherError = 'Failed to redeem voucher. Please try again.';
    } finally {
      voucherLoading = false;
    }
  }

  async function handleTopUp() {
    if (!userPrincipal || topUpAmount < 1 || topUpAmount > 50) return;
    
    topUpLoading = true;
    topUpError = null;
    
    try {
      const response = await fetch(`${BILLING_SERVICE_URL}/checkout/create-session`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          principal_id: userPrincipal.toText(),
          amount: topUpAmount,
        }),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create checkout session');
      }
      
      const data = await response.json();
      
      // Redirect to Stripe checkout
      window.location.href = data.checkout_url;
    } catch (err) {
      console.error('Top-up failed:', err);
      topUpError = err.message;
    } finally {
      topUpLoading = false;
    }
  }
</script>

<svelte:head>
  <title>{$_('dashboard.title')} | Realms</title>
</svelte:head>

<div class="dashboard-page">
  <div class="dashboard-container">
    <!-- Header -->
    <header class="dashboard-header">
      <a href="/" class="back-link">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 12H5M12 19l-7-7 7-7"/>
        </svg>
        {$_('dashboard.back_to_realms')}
      </a>
      <h1>{$_('dashboard.title')}</h1>
      {#if userPrincipal}
        <div class="principal-display">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
          <span class="principal-text">{userPrincipal.toText()}</span>
        </div>
      {/if}
    </header>

    {#if loading}
      <div class="loading-container">
        <div class="spinner"></div>
        <p>{$_('dashboard.loading')}</p>
      </div>
    {:else}
      <!-- Tabs -->
      <div class="tabs">
        <button 
          class="tab" 
          class:active={activeTab === 'credits'}
          on:click={() => activeTab = 'credits'}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="16"></line>
            <line x1="8" y1="12" x2="16" y2="12"></line>
          </svg>
          {$_('dashboard.credits_tab')}
        </button>
        <button 
          class="tab" 
          class:active={activeTab === 'realms'}
          on:click={() => activeTab = 'realms'}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
            <polyline points="9 22 9 12 15 12 15 22"></polyline>
          </svg>
          {$_('dashboard.realms_tab')}
        </button>
      </div>

      <!-- Tab Content -->
      <div class="tab-content">
        {#if activeTab === 'credits'}
          <div class="credits-section">
            <!-- Balance Card -->
            <div class="balance-card">
              <div class="balance-label">{$_('dashboard.current_balance')}</div>
              {#if loadingCredits}
                <div class="balance-loading"></div>
              {:else}
                <div class="balance-value">{balance}</div>
              {/if}
              <div class="balance-unit">{$_('dashboard.credits_unit')}</div>
            </div>

            <!-- Voucher Redemption Section -->
            <div class="voucher-section">
              <h3>Redeem Voucher</h3>
              <p class="voucher-description">Have a voucher code? Enter it below to redeem credits.</p>
              
              <div class="voucher-form">
                <div class="voucher-input-group">
                  <input 
                    type="text" 
                    bind:value={voucherCode}
                    placeholder="Enter voucher code"
                    class="voucher-input"
                    class:error={voucherError}
                    disabled={voucherLoading}
                  />
                  <button 
                    class="voucher-btn"
                    on:click={handleRedeemVoucher}
                    disabled={voucherLoading || !voucherCode.trim()}
                  >
                    {#if voucherLoading}
                      <div class="btn-spinner"></div>
                    {:else}
                      Redeem
                    {/if}
                  </button>
                </div>
                
                {#if voucherError}
                  <div class="error-message">{voucherError}</div>
                {/if}
                
                {#if voucherSuccess}
                  <div class="success-message">{voucherSuccess}</div>
                {/if}
              </div>
            </div>

            <!-- Top-up Section -->
            <div class="topup-section">
              <h3>{$_('dashboard.topup_title')}</h3>
              <p class="topup-description">
                {$_('dashboard.topup_description')}
                <a href="/faq" class="help-link" title="Learn more about credits" aria-label="Learn more about credits">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                    <circle cx="12" cy="12" r="10"></circle>
                    <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
                    <line x1="12" y1="17" x2="12.01" y2="17"></line>
                  </svg>
                </a>
              </p>
              
              <div class="topup-form">
                <div class="amount-input-group">
                  <label for="topup-amount">{$_('dashboard.topup_amount')}</label>
                  <div class="amount-controls">
                    <button 
                      class="amount-btn"
                      on:click={() => topUpAmount = Math.max(1, topUpAmount - 1)}
                      disabled={topUpAmount <= 1}
                    >−</button>
                    <input 
                      type="number" 
                      id="topup-amount"
                      bind:value={topUpAmount}
                      min="1"
                      max="50"
                      class="amount-input"
                    />
                    <button 
                      class="amount-btn"
                      on:click={() => topUpAmount = Math.min(50, topUpAmount + 1)}
                      disabled={topUpAmount >= 50}
                    >+</button>
                  </div>
                  <div class="amount-range">1 - 50 {$_('dashboard.credits_unit')}</div>
                </div>

                <div class="topup-summary">
                  <div class="summary-row">
                    <span>{$_('dashboard.topup_credits')}</span>
                    <span>{topUpAmount} {$_('dashboard.credits_unit')}</span>
                  </div>
                  <div class="summary-row total">
                    <span>{$_('dashboard.topup_total')}</span>
                    <span>${topUpAmount}.00 USD</span>
                  </div>
                </div>

                {#if topUpError}
                  <div class="error-message">{topUpError}</div>
                {/if}

                <button 
                  class="topup-btn"
                  on:click={handleTopUp}
                  disabled={topUpLoading || topUpAmount < 1 || topUpAmount > 50}
                >
                  {#if topUpLoading}
                    <div class="btn-spinner"></div>
                    {$_('dashboard.processing')}
                  {:else}
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect>
                      <line x1="1" y1="10" x2="23" y2="10"></line>
                    </svg>
                    {$_('dashboard.topup_button')}
                  {/if}
                </button>
              </div>
            </div>

            <!-- Redeemed Vouchers -->
            {#if redeemedVouchers.length > 0}
              <div class="history-section">
                <h3>Redeemed Vouchers</h3>
                <ul class="purchase-list">
                  {#each redeemedVouchers as voucher}
                    <li class="purchase-item">
                      <div class="purchase-info">
                        <span class="purchase-amount">+{voucher.credits} {$_('dashboard.credits_unit')}</span>
                        <span class="purchase-date">Code: {voucher.code}</span>
                      </div>
                      <span class="voucher-badge" class:active={voucher.status === 'active'}>
                        {voucher.status === 'active' ? 'Active' : 'Used'}
                      </span>
                    </li>
                  {/each}
                </ul>
              </div>
            {/if}

            <!-- Purchase History -->
            <div class="history-section">
              <h3>{$_('dashboard.purchase_history')}</h3>
              {#if loadingCredits}
                <div class="loading-placeholder"></div>
              {:else if purchases.length === 0 && redeemedVouchers.length === 0}
                <div class="empty-state">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
                    <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                    <line x1="8" y1="21" x2="16" y2="21"></line>
                    <line x1="12" y1="17" x2="12" y2="21"></line>
                  </svg>
                  <p>{$_('dashboard.no_purchases')}</p>
                </div>
              {:else if purchases.length > 0}
                <ul class="purchase-list">
                  {#each purchases as purchase}
                    <li class="purchase-item">
                      <div class="purchase-info">
                        <span class="purchase-amount">+{purchase.amount} {$_('dashboard.credits_unit')}</span>
                        <span class="purchase-date">{formatDate(purchase.date)}</span>
                      </div>
                      <span class="purchase-price">${purchase.price}</span>
                    </li>
                  {/each}
                </ul>
              {:else}
                <p class="no-purchases-note">No card purchases yet</p>
              {/if}
            </div>
          </div>

        {:else if activeTab === 'realms'}
          <div class="realms-section">
            <!-- Active Deployments -->
            {#if deployments.length > 0}
              <div class="realms-group deployments-group">
                <h3>Deployments</h3>
                <ul class="deployment-list">
                  {#each deployments as deployment}
                    <li class="deployment-item">
                      <div class="deployment-info">
                        <span class="deployment-name">{deployment.realm_name}</span>
                        <span class="deployment-date">{formatDate(deployment.created_at)}</span>
                      </div>
                      <div class="deployment-status-row">
                        <span 
                          class="deployment-status"
                          style="background-color: {getDeploymentStatusColor(deployment.status)}20; color: {getDeploymentStatusColor(deployment.status)}; border-color: {getDeploymentStatusColor(deployment.status)}"
                        >
                          {#if deployment.status === 'in_progress'}
                            <span class="spinner-tiny"></span>
                          {/if}
                          {getDeploymentStatusLabel(deployment.status)}
                        </span>
                        {#if deployment.status === 'completed' && deployment.realm_url}
                          <a href={deployment.realm_url} target="_blank" rel="noopener noreferrer" class="visit-btn">
                            Visit Realm →
                          </a>
                        {/if}
                        {#if deployment.status === 'failed' && deployment.error}
                          <span class="deployment-error" title={deployment.error}>Error</span>
                        {/if}
                      </div>
                      {#if deployment.credits_charged > 0}
                        <span class="credits-charged">-{deployment.credits_charged} credits</span>
                      {/if}
                    </li>
                  {/each}
                </ul>
              </div>
            {/if}

            <!-- Deployments in Progress -->
            {#if deployments.length > 0}
              <div class="realms-group deployments-section">
                <h3>🚀 Deployments in Progress</h3>
                <ul class="deployment-list">
                  {#each deployments as deployment}
                    <li class="deployment-item">
                      <div class="deployment-header">
                        <span class="deployment-name">{deployment.realm_name || 'Unnamed Realm'}</span>
                        <span class="deployment-status status-{deployment.status}">
                          {#if deployment.status === 'running'}
                            <span class="status-spinner"></span>
                          {/if}
                          {deployment.status}
                        </span>
                      </div>
                      <div class="deployment-id">ID: {deployment.deployment_id}</div>
                      <div class="deployment-time">Started: {formatDate(deployment.started_at)}</div>
                      {#if deployment.status === 'completed' && deployment.frontend_url}
                        <a href={deployment.frontend_url} target="_blank" rel="noopener noreferrer" class="deployment-link">
                          Visit Realm →
                        </a>
                      {/if}
                      {#if deployment.status === 'failed' && deployment.error}
                        <div class="deployment-error">{deployment.error}</div>
                      {/if}
                    </li>
                  {/each}
                </ul>
              </div>
            {/if}

            <!-- Created Realms -->
            <div class="realms-group">
              <h3>{$_('dashboard.created_realms')}</h3>
              {#if loadingDeployments}
                <div class="loading-placeholder"></div>
              {:else if deployments.length === 0}
                <div class="empty-state">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
                    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
                    <polyline points="9 22 9 12 15 12 15 22"></polyline>
                  </svg>
                  <p>{$_('dashboard.no_created_realms')}</p>
                  <a href="/create-realm" class="create-realm-btn">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M12 5v14M5 12h14"/>
                    </svg>
                    Create Realm
                  </a>
                </div>
              {:else}
                <ul class="realm-list">
                  {#each deployments as deployment}
                    <li class="realm-item">
                      <div class="realm-info">
                        <span class="realm-name">{deployment.realm_name || deployment.realm_id}</span>
                        <span class="realm-id">{deployment.realm_id}</span>
                      </div>
                      <div class="realm-status-row">
                        <span class="deployment-status {deployment.status}">{deployment.status}</span>
                        {#if deployment.status === 'completed' && deployment.frontend_url}
                          <a href={deployment.frontend_url} target="_blank" rel="noopener noreferrer" class="realm-visit-link">
                            Visit →
                          </a>
                        {/if}
                      </div>
                    </li>
                  {/each}
                </ul>
              {/if}
            </div>

            <!-- Joined Realms -->
            <div class="realms-group">
              <h3>{$_('dashboard.joined_realms')}</h3>
              {#if loadingRealms}
                <div class="loading-placeholder"></div>
              {:else if joinedRealms.length === 0}
                <div class="empty-state">
                  <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                    <circle cx="9" cy="7" r="4"></circle>
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                    <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                  </svg>
                  <p>{$_('dashboard.no_joined_realms')}</p>
                </div>
              {:else}
                <ul class="realm-list">
                  {#each joinedRealms as realm}
                    <li class="realm-item">
                      <div class="realm-info">
                        <span class="realm-name">{realm.name}</span>
                        <span class="realm-id">{realm.id}</span>
                      </div>
                      <span class="role-badge member">{$_('dashboard.role_member')}</span>
                    </li>
                  {/each}
                </ul>
              {/if}
            </div>
          </div>
        {/if}
      </div>
    {/if}
  </div>
</div>

<style>
  .dashboard-page {
    min-height: 100vh;
    background: #FAFAFA;
    padding: 2rem;
  }

  .dashboard-container {
    max-width: 800px;
    margin: 0 auto;
  }

  .dashboard-header {
    margin-bottom: 2rem;
  }

  .back-link {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    color: #525252;
    text-decoration: none;
    font-size: 0.875rem;
    margin-bottom: 1rem;
    transition: color 0.15s ease;
  }

  .back-link:hover {
    color: #171717;
  }

  .dashboard-header h1 {
    font-size: 2rem;
    font-weight: 700;
    color: #171717;
    margin: 0 0 1rem 0;
  }

  .principal-display {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: #F5F5F5;
    padding: 0.75rem 1rem;
    border-radius: 0.5rem;
    font-family: monospace;
    font-size: 0.75rem;
    color: #525252;
    overflow: hidden;
  }

  .principal-text {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 4rem;
    color: #525252;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 3px solid #E5E5E5;
    border-top-color: #171717;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .tabs {
    display: flex;
    gap: 0.5rem;
    border-bottom: 1px solid #E5E5E5;
    margin-bottom: 1.5rem;
  }

  .tab {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1.5rem;
    border: none;
    background: none;
    color: #525252;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
    transition: all 0.15s ease;
  }

  .tab:hover {
    color: #171717;
  }

  .tab.active {
    color: #171717;
    border-bottom-color: #171717;
  }

  .tab-content {
    background: #FFFFFF;
    border-radius: 1rem;
    padding: 1.5rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  /* Credits Section */
  .balance-card {
    background: linear-gradient(135deg, #171717 0%, #404040 100%);
    color: #FFFFFF;
    padding: 2rem;
    border-radius: 1rem;
    text-align: center;
    margin-bottom: 2rem;
  }

  .balance-label {
    font-size: 0.875rem;
    opacity: 0.8;
    margin-bottom: 0.5rem;
  }

  .balance-value {
    font-size: 3rem;
    font-weight: 700;
    line-height: 1;
    margin-bottom: 0.25rem;
  }

  .balance-unit {
    font-size: 0.875rem;
    opacity: 0.8;
  }

  .balance-loading {
    width: 60px;
    height: 48px;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 0.5rem;
    margin: 0 auto;
    animation: pulse 1.5s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  /* Top-up Section */
  .topup-section {
    background: #F5F5F5;
    border-radius: 1rem;
    padding: 1.5rem;
    margin-bottom: 2rem;
  }

  .topup-section h3 {
    font-size: 1.125rem;
    font-weight: 600;
    color: #171717;
    margin: 0 0 0.5rem 0;
  }

  .topup-description {
    color: #525252;
    font-size: 0.875rem;
    margin: 0 0 1.5rem 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .help-link {
    display: inline-flex;
    align-items: center;
    color: #737373;
    transition: color 0.15s ease;
  }

  .help-link:hover {
    color: #171717;
  }

  .topup-form {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .amount-input-group {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .amount-input-group label {
    font-size: 0.875rem;
    font-weight: 500;
    color: #171717;
  }

  .amount-controls {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .amount-btn {
    width: 40px;
    height: 40px;
    border: 1px solid #E5E5E5;
    background: #FFFFFF;
    border-radius: 0.5rem;
    font-size: 1.25rem;
    color: #171717;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .amount-btn:hover:not(:disabled) {
    background: #F5F5F5;
  }

  .amount-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .amount-input {
    width: 100px;
    height: 40px;
    border: 1px solid #E5E5E5;
    border-radius: 0.5rem;
    text-align: center;
    font-size: 1.125rem;
    font-weight: 600;
    color: #171717;
  }

  .amount-input:focus {
    outline: none;
    border-color: #171717;
  }

  .amount-range {
    font-size: 0.75rem;
    color: #737373;
  }

  .topup-summary {
    background: #FFFFFF;
    border-radius: 0.5rem;
    padding: 1rem;
  }

  .summary-row {
    display: flex;
    justify-content: space-between;
    padding: 0.5rem 0;
    font-size: 0.875rem;
    color: #525252;
  }

  .summary-row.total {
    border-top: 1px solid #E5E5E5;
    margin-top: 0.5rem;
    padding-top: 1rem;
    font-weight: 600;
    color: #171717;
    font-size: 1rem;
  }

  .error-message {
    background: #FEE2E2;
    color: #DC2626;
    padding: 0.75rem 1rem;
    border-radius: 0.5rem;
    font-size: 0.875rem;
  }

  .success-message {
    background: #D1FAE5;
    color: #059669;
    padding: 0.75rem 1rem;
    border-radius: 0.5rem;
    font-size: 0.875rem;
  }

  /* Voucher Section */
  .voucher-section {
    background: #F0FDF4;
    border: 1px solid #BBF7D0;
    border-radius: 1rem;
    padding: 1.5rem;
    margin-bottom: 2rem;
  }

  .voucher-section h3 {
    font-size: 1.125rem;
    font-weight: 600;
    color: #171717;
    margin: 0 0 0.5rem 0;
  }

  .voucher-description {
    color: #525252;
    font-size: 0.875rem;
    margin: 0 0 1rem 0;
  }

  .voucher-form {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .voucher-input-group {
    display: flex;
    gap: 0.5rem;
  }

  .voucher-input {
    flex: 1;
    height: 44px;
    border: 1px solid #E5E5E5;
    border-radius: 0.5rem;
    padding: 0 1rem;
    font-size: 1rem;
    text-transform: uppercase;
    background: #FFFFFF;
  }

  .voucher-input:focus {
    outline: none;
    border-color: #22C55E;
  }

  .voucher-input.error {
    border-color: #DC2626;
  }

  .voucher-input:disabled {
    background: #F5F5F5;
  }

  .voucher-btn {
    height: 44px;
    padding: 0 1.5rem;
    background: #22C55E;
    color: #FFFFFF;
    border: none;
    border-radius: 0.5rem;
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 100px;
  }

  .voucher-btn:hover:not(:disabled) {
    background: #16A34A;
  }

  .voucher-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .voucher-badge {
    padding: 0.25rem 0.75rem;
    border-radius: 1rem;
    font-size: 0.75rem;
    font-weight: 500;
    background: #F5F5F5;
    color: #737373;
  }

  .voucher-badge.active {
    background: #D1FAE5;
    color: #059669;
  }

  .no-purchases-note {
    color: #737373;
    font-size: 0.875rem;
    text-align: center;
    padding: 1rem;
    margin: 0;
  }

  .topup-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    width: 100%;
    padding: 1rem;
    background: #171717;
    color: #FFFFFF;
    border: none;
    border-radius: 0.5rem;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s ease;
  }

  .topup-btn:hover:not(:disabled) {
    background: #404040;
  }

  .topup-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-spinner {
    width: 18px;
    height: 18px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: #FFFFFF;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  /* History Section */
  .history-section h3,
  .realms-group h3 {
    font-size: 1rem;
    font-weight: 600;
    color: #171717;
    margin: 0 0 1rem 0;
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 2rem;
    color: #737373;
    text-align: center;
  }

  .empty-state svg {
    margin-bottom: 1rem;
    opacity: 0.5;
  }

  .empty-state p {
    margin: 0;
    font-size: 0.875rem;
  }

  .create-realm-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 1rem;
    padding: 0.75rem 1.5rem;
    background: #171717;
    color: #FFFFFF;
    border-radius: 0.5rem;
    text-decoration: none;
    font-size: 0.875rem;
    font-weight: 600;
    transition: background 0.15s ease;
  }

  .create-realm-btn:hover {
    background: #404040;
  }

  .loading-placeholder {
    height: 100px;
    background: #F5F5F5;
    border-radius: 0.5rem;
    animation: pulse 1.5s ease-in-out infinite;
  }

  .purchase-list,
  .realm-list {
    list-style: none;
    padding: 0;
    margin: 0;
  }

  .purchase-item,
  .realm-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem;
    border-bottom: 1px solid #F5F5F5;
  }

  .purchase-item:last-child,
  .realm-item:last-child {
    border-bottom: none;
  }

  .purchase-info,
  .realm-info {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .purchase-amount {
    font-weight: 600;
    color: #059669;
  }

  .purchase-date,
  .realm-id {
    font-size: 0.75rem;
    color: #737373;
    font-family: monospace;
  }

  .realm-status-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .realm-visit-link {
    font-size: 0.75rem;
    color: #2563EB;
    text-decoration: none;
  }

  .realm-visit-link:hover {
    text-decoration: underline;
  }

  .purchase-price {
    font-weight: 500;
    color: #171717;
  }

  .realm-name {
    font-weight: 500;
    color: #171717;
  }

  .role-badge {
    padding: 0.25rem 0.75rem;
    border-radius: 1rem;
    font-size: 0.75rem;
    font-weight: 500;
  }

  .role-badge.owner {
    background: #DBEAFE;
    color: #1D4ED8;
  }

  .role-badge.member {
    background: #D1FAE5;
    color: #059669;
  }

  /* Realms Section */
  .realms-group {
    margin-bottom: 2rem;
  }

  .realms-group:last-child {
    margin-bottom: 0;
  }

  /* Deployments Section */
  .deployments-group {
    background: #F0FDF4;
    border: 1px solid #BBF7D0;
    border-radius: 0.75rem;
    padding: 1rem;
  }

  .deployment-list {
    list-style: none;
    padding: 0;
    margin: 0;
  }

  .deployment-item {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    padding: 1rem;
    background: #FFFFFF;
    border-radius: 0.5rem;
    margin-bottom: 0.5rem;
    border: 1px solid #E5E5E5;
  }

  .deployment-item:last-child {
    margin-bottom: 0;
  }

  .deployment-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .deployment-name {
    font-weight: 600;
    color: #171717;
  }

  .deployment-date {
    font-size: 0.75rem;
    color: #737373;
  }

  .deployment-status-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .deployment-status {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.25rem 0.75rem;
    border-radius: 1rem;
    font-size: 0.75rem;
    font-weight: 500;
    border: 1px solid;
  }

  .spinner-tiny {
    width: 12px;
    height: 12px;
    border: 2px solid currentColor;
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  .visit-btn {
    font-size: 0.75rem;
    color: #2563EB;
    text-decoration: none;
    font-weight: 500;
  }

  .visit-btn:hover {
    text-decoration: underline;
  }

  .deployment-error {
    font-size: 0.75rem;
    color: #EF4444;
    cursor: help;
  }

  .credits-charged {
    font-size: 0.75rem;
    color: #737373;
  }

  /* Deployments in My Realms section */
  .deployments-section {
    background: #FEF3C7;
    border: 1px solid #FCD34D;
    border-radius: 0.75rem;
    padding: 1rem;
  }

  .deployments-section h3 {
    color: #92400E;
  }

  .deployment-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .deployment-id,
  .deployment-time {
    font-size: 0.75rem;
    color: #737373;
  }

  .deployment-link {
    font-size: 0.875rem;
    color: #2563EB;
    font-weight: 500;
    text-decoration: none;
  }

  .deployment-link:hover {
    text-decoration: underline;
  }

  .status-spinner {
    width: 12px;
    height: 12px;
    border: 2px solid #F59E0B;
    border-top-color: transparent;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    display: inline-block;
  }

  .status-running {
    background: #FEF3C7;
    border-color: #FCD34D;
    color: #92400E;
  }

  .status-completed {
    background: #D1FAE5;
    border-color: #6EE7B7;
    color: #065F46;
  }

  .status-failed {
    background: #FEE2E2;
    border-color: #FCA5A5;
    color: #991B1B;
  }

  /* Responsive */
  @media (max-width: 768px) {
    .dashboard-page {
      padding: 1rem;
    }

    .dashboard-header h1 {
      font-size: 1.5rem;
    }

    .balance-value {
      font-size: 2.5rem;
    }

    .tab-content {
      padding: 1rem;
    }

    .topup-section {
      padding: 1rem;
    }
  }
</style>
