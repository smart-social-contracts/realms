<script lang="ts">
  import { _ } from 'svelte-i18n';
  import { backend } from '$lib/canisters';
  import { principal } from '$lib/stores/auth';
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { Button, Input, Label, Select, Modal } from 'flowbite-svelte';
  
  interface PaymentAccount {
    id: string;
    address: string;
    label: string;
    network: string;
    currency: string;
    is_verified: boolean;
    created_at: string;
  }
  
  let accounts: PaymentAccount[] = [];
  let loading = false;
  let showAddModal = false;
  let errorMessage = '';
  let successMessage = '';
  
  // Form fields
  let newAddress = '';
  let newLabel = '';
  let newNetwork = 'ICP';
  let newCurrency = 'ICP';
  
  // Network and currency options
  const networks = [
    { value: 'ICP', label: 'Internet Computer (ICP)' },
    { value: 'Bitcoin', label: 'Bitcoin' },
    { value: 'Ethereum', label: 'Ethereum' },
    { value: 'SEPA', label: 'SEPA Bank Transfer' },
  ];
  
  const currenciesByNetwork: Record<string, Array<{ value: string; label: string }>> = {
    ICP: [
      { value: 'ICP', label: 'ICP' },
      { value: 'ckBTC', label: 'ckBTC' },
      { value: 'ckETH', label: 'ckETH' },
    ],
    Bitcoin: [{ value: 'BTC', label: 'Bitcoin (BTC)' }],
    Ethereum: [
      { value: 'ETH', label: 'Ethereum (ETH)' },
      { value: 'USDC', label: 'USDC' },
      { value: 'USDT', label: 'USDT' },
    ],
    SEPA: [{ value: 'EUR', label: 'Euro (EUR)' }],
  };
  
  $: availableCurrencies = currenciesByNetwork[newNetwork] || [];
  
  // Update currency when network changes
  $: if (availableCurrencies.length > 0 && !availableCurrencies.find(c => c.value === newCurrency)) {
    newCurrency = availableCurrencies[0].value;
  }

  // Load accounts when component mounts
  onMount(() => {
    loadAccounts();
  });
  
  async function loadAccounts() {
    loading = true;
    errorMessage = '';
    try {
      // Use extension API to list payment accounts for current user
      const response = await backend.extension_sync_call({
        extension_name: 'member_dashboard',
        function_name: 'list_payment_accounts',
        args: JSON.stringify({ user_id: $principal }),
        kwargs: null
      });
      
      if (response.success) {
        const result = JSON.parse(response.response);
        if (result.success && result.data) {
          accounts = result.data;
        } else {
          errorMessage = result.error || 'Failed to load payment accounts';
        }
      } else {
        errorMessage = 'Failed to load payment accounts';
      }
    } catch (error) {
      console.error('Failed to load payment accounts:', error);
      errorMessage = 'Failed to load payment accounts. Please try again.';
    } finally {
      loading = false;
    }
  }
  
  async function addAccount() {
    if (!newAddress || !newLabel) {
      errorMessage = 'Address and label are required';
      return;
    }
    
    loading = true;
    errorMessage = '';
    successMessage = '';
    
    try {
      // Use extension API to create new payment account
      const response = await backend.extension_sync_call({
        extension_name: 'member_dashboard',
        function_name: 'add_payment_account',
        args: JSON.stringify({
          user_id: $principal,
          address: newAddress,
          label: newLabel,
          network: newNetwork,
          currency: newCurrency,
        }),
        kwargs: null
      });
      
      if (response.success) {
        const result = JSON.parse(response.response);
        if (result.success) {
          successMessage = 'Payment account added successfully';
          await loadAccounts();
          resetForm();
          showAddModal = false;
        } else {
          errorMessage = result.error || 'Failed to add payment account';
        }
      } else {
        errorMessage = 'Failed to add payment account';
      }
    } catch (error) {
      console.error('Failed to add payment account:', error);
      errorMessage = 'Failed to add payment account. Please try again.';
    } finally {
      loading = false;
    }
  }
  
  async function removeAccount(accountId: string) {
    if (!confirm($_('extensions.member_dashboard.confirm_remove_payment_account'))) {
      return;
    }
    
    loading = true;
    errorMessage = '';
    successMessage = '';
    
    try {
      // Use extension API to soft delete (set is_active to false)
      const response = await backend.extension_sync_call({
        extension_name: 'member_dashboard',
        function_name: 'remove_payment_account',
        args: JSON.stringify({
          user_id: $principal,
          account_id: accountId
        }),
        kwargs: null
      });
      
      if (response.success) {
        const result = JSON.parse(response.response);
        if (result.success) {
          successMessage = 'Payment account removed successfully';
          await loadAccounts();
        } else {
          errorMessage = result.error || 'Failed to remove payment account';
        }
      } else {
        errorMessage = 'Failed to remove payment account';
      }
    } catch (error) {
      console.error('Failed to remove payment account:', error);
      errorMessage = 'Failed to remove payment account. Please try again.';
    } finally {
      loading = false;
    }
  }
  
  function resetForm() {
    newAddress = '';
    newLabel = '';
    newNetwork = 'ICP';
    newCurrency = 'ICP';
    errorMessage = '';
    successMessage = '';
  }
  
  function getNetworkLabel(networkValue: string): string {
    return networks.find(n => n.value === networkValue)?.label || networkValue;
  }
  
  onMount(() => {
    loadAccounts();
  });
</script>

<div class="payment-accounts-container">
  <div class="header">
    <h3 class="text-xl font-semibold text-gray-900 dark:text-white">
      {$_('extensions.member_dashboard.payment_accounts')}
    </h3>
    <Button color="alternative" size="sm" on:click={() => showAddModal = true} disabled={loading}>
      + {$_('extensions.member_dashboard.add_payment_account')}
    </Button>
  </div>
  
  {#if errorMessage}
    <div class="alert alert-error">
      {errorMessage}
    </div>
  {/if}
  
  {#if successMessage}
    <div class="alert alert-success">
      {successMessage}
    </div>
  {/if}
  
  {#if loading && accounts.length === 0}
    <p class="text-gray-600">{$_('extensions.member_dashboard.loading')}</p>
  {:else if accounts.length === 0}
    <div class="empty-state">
      <p class="text-gray-600">{$_('extensions.member_dashboard.no_payment_accounts')}</p>
      <p class="text-sm text-gray-500 mt-2">
        {$_('extensions.member_dashboard.payment_accounts_description')}
      </p>
    </div>
  {:else}
    <div class="accounts-grid">
      {#each accounts as account}
        <div class="account-card">
          <div class="account-header">
            <div class="account-label-row">
              <strong class="text-lg">{account.label}</strong>
              {#if account.is_verified}
                <span class="verified-badge">
                  ✓ {$_('extensions.member_dashboard.verified')}
                </span>
              {/if}
            </div>
            <div class="badge-row">
              <span class="network-badge">{getNetworkLabel(account.network)}</span>
              <span class="currency-badge">{account.currency}</span>
            </div>
          </div>
          
          <div class="account-body">
            <div class="address-container">
              <code class="address-text">{account.address}</code>
            </div>
            <p class="text-xs text-gray-500 mt-2">
              {$_('extensions.member_dashboard.created_at')}: {new Date(account.created_at).toLocaleDateString()}
            </p>
          </div>
          
          <div class="account-actions">
            <Button
              color="alternative"
              size="xs"
              on:click={() => removeAccount(account.id)}
              disabled={loading}
            >
              🗑️ {$_('extensions.member_dashboard.remove')}
            </Button>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- Add Payment Account Modal -->
<Modal bind:open={showAddModal} size="md" autoclose={false}>
  <h3 slot="header" class="text-xl font-semibold text-gray-900 dark:text-white">
    {$_('extensions.member_dashboard.add_payment_account')}
  </h3>
  
  <div class="space-y-4">
    <div>
      <Label for="account-label">{$_('extensions.member_dashboard.account_label')}</Label>
      <Input
        id="account-label"
        bind:value={newLabel}
        placeholder={$_('extensions.member_dashboard.account_label_placeholder')}
      />
    </div>
    
    <div>
      <Label for="network">{$_('extensions.member_dashboard.network')}</Label>
      <Select id="network" bind:value={newNetwork}>
        {#each networks as network}
          <option value={network.value}>{network.label}</option>
        {/each}
      </Select>
    </div>
    
    <div>
      <Label for="currency">{$_('extensions.member_dashboard.currency')}</Label>
      <Select id="currency" bind:value={newCurrency}>
        {#each availableCurrencies as currency}
          <option value={currency.value}>{currency.label}</option>
        {/each}
      </Select>
    </div>
    
    <div>
      <Label for="address">{$_('extensions.member_dashboard.address')}</Label>
      <Input
        id="address"
        bind:value={newAddress}
        placeholder={$_('extensions.member_dashboard.address_placeholder')}
      />
    </div>
    
    {#if errorMessage}
      <div class="p-4 mb-4 text-sm text-red-800 rounded-lg bg-red-50 dark:bg-gray-800 dark:text-red-400">
        {errorMessage}
      </div>
    {/if}
  </div>
  
  <svelte:fragment slot="footer">
    <div class="flex justify-end gap-2 w-full">
      <Button color="alternative" on:click={() => { showAddModal = false; resetForm(); }} disabled={loading}>
        {$_('extensions.member_dashboard.cancel')}
      </Button>
      <Button color="alternative" on:click={addAccount} disabled={loading}>
        {$_('extensions.member_dashboard.save')}
      </Button>
    </div>
  </svelte:fragment>
</Modal>

<style>
  .payment-accounts-container {
    padding: 1.5rem;
    max-width: 100%;
    overflow-x: auto;
  }
  
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
  }
  
  .alert {
    padding: 0.75rem 1rem;
    border-radius: 0.5rem;
    margin-bottom: 1rem;
  }
  
  .alert-error {
    background-color: #fee;
    color: #c00;
    border: 1px solid #fcc;
  }
  
  .alert-success {
    background-color: #efe;
    color: #060;
    border: 1px solid #cfc;
  }
  
  .empty-state {
    text-align: center;
    padding: 3rem 1rem;
    background: #f9fafb;
    border-radius: 0.5rem;
  }
  
  .accounts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 1.5rem;
  }
  
  .account-card {
    border: 1px solid #e5e7eb;
    border-radius: 0.75rem;
    padding: 1.5rem;
    background: white;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    transition: box-shadow 0.2s;
  }
  
  .account-card:hover {
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  }
  
  .account-header {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .account-label-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;
  }
  
  .badge-row {
    display: flex;
    gap: 0.5rem;
  }
  
  .network-badge, .currency-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 500;
  }
  
  .network-badge {
    background: #dbeafe;
    color: #1e40af;
  }
  
  .currency-badge {
    background: #fef3c7;
    color: #92400e;
  }
  
  .verified-badge {
    background: #d1fae5;
    color: #065f46;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 500;
  }
  
  .account-body {
    flex-grow: 1;
  }
  
  .address-container {
    background: #f9fafb;
    padding: 0.75rem;
    border-radius: 0.5rem;
    overflow-x: auto;
  }
  
  .address-text {
    font-family: 'Courier New', Courier, monospace;
    font-size: 0.875rem;
    color: #374151;
    word-break: break-all;
  }
  
  .account-actions {
    display: flex;
    justify-content: flex-end;
    padding-top: 0.5rem;
    border-top: 1px solid #e5e7eb;
  }
</style>
