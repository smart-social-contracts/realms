<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, Tabs, TabItem, Spinner, Button, Input, Alert, Table, TableHead, TableHeadCell, TableBody, TableBodyRow, TableBodyCell } from 'flowbite-svelte';
	import { ChartPieSolid, ClockSolid, WalletSolid, UsersSolid,
		ChartOutline, PaperPlaneSolid, DollarOutline } from 'flowbite-svelte-icons';
	import { principal } from '$lib/stores/auth';
	import { formatNumber } from '$lib/utils';
	import TransactionsList from './TransactionsList.svelte';
	import BalanceCard from './BalanceCard.svelte';
	
	// Import backend directly without using await in top-level
	import { backend } from '$lib/canisters';
	import { _ } from 'svelte-i18n';
	
	// Component state
	let loading = true;
	let error = '';
	let activeTab = 0;
	let balanceData = null;
	let vaultStatus = null;
	let transactions = [];
	let totalTransactions = 0;
	let accounts = [];
	
	// Principal ID management
	let userPrincipalId = $principal || "";
	
	// Vault canister ID management
	let vaultCanisterId = ""; // No default - user must specify
	let vaultCanisterInputValue = vaultCanisterId;
	let vaultCanisterError = '';
	
	// Transfer form data
	let transferRecipient = '';
	let transferAmount = '';
	let transferMemo = '';
	let transferLoading = false;
	let transferSuccess = false;
	let transferError = '';
	
	// Format amounts for display (ckBTC uses 8 decimal places)
	function formatCkBTC(amount) {
	    return formatNumber(amount / 100000000, 8);
	}
	
	// Get vault balance for current user
	async function getBalance() {
		try {
			// Prepare call parameters
			const callParams = { 
				principal_id: vaultCanisterId, // Use the vault canister ID as the principal, same as CLI example
				vault_canister_id: vaultCanisterId
			};
			
			// Log the request details
			console.log('Calling get_balance with parameters:', callParams);
			
			// Use the extension_async_call API method with proper arguments including vault_canister_id
			const response = await backend.extension_async_call({
				extension_name: "vault_manager",
				function_name: "get_balance",
				args: JSON.stringify(callParams)
			});
			
			console.log('Balance response:', response);
			
			if (response.success) {
				// Parse the JSON response
				const data = JSON.parse(response.response);
				console.log('Parsed balance data:', data);
				
				if (data.success) {
					// Handle successful balance response
					balanceData = {
						balance: data.data.Balance?.amount || 0,
						token: "ckBTC",
						principalId: data.data.Balance?.principal_id || vaultCanisterId
					};
					console.log('Balance data set:', balanceData);
				} else {
					// Handle vault error (e.g., balance not found)
					console.log('Vault returned error:', data.error);
					balanceData = {
						balance: 0,
						token: "ckBTC", 
						principalId: vaultCanisterId,
						error: data.error || "Balance not found"
					};
				}
			} else {
				error = `Failed to get balance: ${response.response}`;
				console.error(error);
			}
		} catch (err) {
			console.error('Error fetching balance:', err);
			error = `Error fetching balance: ${err.message || err}`;
		}
	}
	
	// Get vault status information
	async function getVaultStatus() {
		try {
			// Prepare call parameters
			const callParams = { 
				vault_canister_id: vaultCanisterId
			};
			
			// Log the request details
			console.log('Calling get_status with parameters:', callParams);
			
			// Use the extension_async_call API method including vault_canister_id
			const response = await backend.extension_async_call({
				extension_name: "vault_manager",
				function_name: "get_status",
				args: JSON.stringify(callParams)
			});
			
			console.log('Status response:', response);
			
			if (response.success) {
				// Parse the JSON response
				const data = JSON.parse(response.response);
				console.log('Parsed status data:', data);
				
				if (data.success && data.data.Stats) {
					const stats = data.data.Stats;
					vaultStatus = {
						version: "1.0.0",
						name: "Realm Vault",
						token: "ckBTC",
						total_supply: stats.app_data?.sync_tx_id || 0,
						accounts: stats.balances?.length || 0,
						admin_principal: stats.app_data?.admin_principal || "Unknown",
						sync_status: stats.app_data?.sync_status || "Unknown"
					};
					
					// Extract accounts data for the Accounts tab
					if (stats.balances && Array.isArray(stats.balances)) {
						accounts = stats.balances.map(account => ({
							principal_id: account.principal_id,
							amount: account.amount
						}));
					}
					
					console.log('Vault status set:', vaultStatus);
					console.log('Accounts set:', accounts);
				} else {
					error = `Failed to get vault status: ${data.error || 'Unknown error'}`;
					console.error(error);
				}
			} else {
				error = `Failed to get vault status: ${response.response}`;
				console.error(error);
			}
		} catch (err) {
			console.error('Error fetching vault status:', err);
			error = `Error fetching vault status: ${err.message || err}`;
		}
	}
	
	// Get recent transactions
	async function getTransactions() {
		try {
			// Prepare call parameters
			const callParams = { 
				principal_id: vaultCanisterId, // Use the vault canister ID directly as the principal
				vault_canister_id: vaultCanisterId
			};
			
			// Log the request details
			console.log('Calling get_transactions with parameters:', callParams);
			
			// Use the extension_async_call API method to get transactions directly from the vault canister
			const response = await backend.extension_async_call({
				extension_name: "vault_manager",
				function_name: "get_transactions",
				args: JSON.stringify(callParams)
			});
			
			console.log('Transactions response:', response);
			
			if (response.success) {
				// Parse the JSON response
				const data = JSON.parse(response.response);
				console.log('Parsed transactions data:', data);
				
				if (data.success && data.data && data.data.Transactions && Array.isArray(data.data.Transactions)) {
					// Format transactions for the UI using the Transactions array
					transactions = data.data.Transactions.map((tx) => {
						// Convert timestamps to milliseconds by dividing by 1,000,000 (nanoseconds to milliseconds)
						const timestamp = parseInt(tx.timestamp) / 1000000;
						
						// Safely handle amount field - ensure it exists and is a string
						const txAmount = tx.amount ? String(tx.amount) : "0";
						
						// Determine if this is an incoming or outgoing transaction
						const isIncoming = !txAmount.startsWith("-");
						const amount = isIncoming ? txAmount : txAmount.substring(1); // Remove minus sign if outgoing
						
						return {
							id: tx.id || "unknown",
							from_principal: isIncoming ? "system" : userPrincipalId,
							to_principal: isIncoming ? userPrincipalId : "recipient",
							amount: parseInt(amount) || 0,
							token: "ckBTC",
							timestamp: timestamp,
							status: "completed"
						};
					});
					totalTransactions = transactions.length;
					console.log('Transactions set:', transactions);
				} else {
					// No transactions found or error
					console.log('No transactions found or error:', data.error);
					transactions = [];
					totalTransactions = 0;
				}
			} else {
				error = `Failed to get transactions: ${response.response}`;
				console.error(error);
			}
		} catch (err) {
			console.error('Error fetching transactions:', err);
			error = `Error fetching transactions: ${err.message || err}`;
		}
	}
	
	// Transfer tokens to another principal
	async function transferTokens() {
		transferLoading = true;
		transferSuccess = false;
		transferError = '';
		
		try {
			// Use the extension_async_call API method including vault_canister_id
			const response = await backend.extension_async_call({
				extension_name: "vault_manager",
				function_name: "transfer",
				args: JSON.stringify({
					to_principal: transferRecipient,
					amount: parseInt(transferAmount),
					vault_canister_id: vaultCanisterId
				})
			});
			
			if (response.success) {
				// Parse the JSON response
				const data = JSON.parse(response.response);
				if (data.success) {
					transferSuccess = true;
					console.log('Transfer successful, tx ID:', data.data.transaction_id);
					resetTransferForm();
					await getBalance();
					await getTransactions(); // Refresh transactions after transfer
				} else {
					transferError = `Transfer failed: ${data.error}`;
				}
			} else {
				transferError = `Transfer failed: ${response.response}`;
			}
		} catch (err) {
			transferError = `Error during transfer: ${err.message}`;
			console.error(transferError);
		} finally {
			transferLoading = false;
		}
	}
	
	// Reset transfer form after successful transfer
	function resetTransferForm() {
		transferRecipient = '';
		transferAmount = '';
		transferMemo = '';
	}
	
	// Load all data
	async function loadData() {
		loading = true;
		error = '';
		
		// Validate canister ID
		if (!vaultCanisterInputValue || vaultCanisterInputValue.trim() === '') {
			vaultCanisterError = 'Please enter a valid vault canister ID';
			loading = false;
			return;
		}
		
		// Set actual values from inputs
		vaultCanisterId = vaultCanisterInputValue;
		userPrincipalId = $principal || ""; // Always use authenticated principal

		try {
			// Run all data fetching in parallel
			await Promise.all([getBalance(), getVaultStatus(), getTransactions()]);
			error = ''; // Clear any previous errors if successful
		} catch (err) {
			console.error('Error loading data:', err);
			error = `Error loading data: ${err.message || err}`;
		} finally {
			loading = false;
		}
	}
	
	// Initialize the component
	onMount(async () => {
		// Only load data if vault canister ID is already set
		if (vaultCanisterId) {
			await loadData();
		} else {
			loading = false; // Stop loading state since we're waiting for user input
		}
	});
</script>

<Card size="lg" padding="xl" class="w-full">
	<div class="flex items-center mb-4">
		<WalletSolid class="mr-2 h-8 w-8 text-primary-600" />
		<h2 class="text-2xl font-bold text-gray-900 dark:text-white">{$_('extensions.vault_manager.title')}</h2>
	</div>

	<!-- Configuration Section -->
	<div class="vault-configuration mb-6">
		<h3 class="text-xl font-bold mb-4">{$_('extensions.vault_manager.configuration.title')}</h3>
		
		<!-- Simplified to only have Vault Canister ID input -->
		<div class="mb-4">
			<Input 
				type="text" 
				id="vault-canister-id" 
				placeholder="Enter vault canister ID" 
				label="Vault Canister ID" 
				bind:value={vaultCanisterInputValue} 
				on:keydown={(e) => e.key === 'Enter' && loadData()}
			/>
			{#if vaultCanisterError}
				<p class="text-red-600 text-sm mt-1">{vaultCanisterError}</p>
			{/if}
		</div>
		
		{#if vaultCanisterId && vaultCanisterId !== vaultCanisterInputValue}
			<div class="text-sm text-gray-600 dark:text-gray-400 mb-2">
				Current Vault: {vaultCanisterId}
			</div>
		{/if}
		
		<Button color="primary" on:click={loadData}>
			{#if loading}
				<div class="flex items-center">
					<Spinner class="mr-2" size="sm" color="white" />
					<span>Loading...</span>
				</div>
			{:else}
				<span>Load Vault</span>
			{/if}
		</Button>
	</div>

	{#if loading}
		<!-- Improved elegant loading animation -->
		<div class="flex items-center justify-center py-12">
			<div class="relative">
				<!-- Animated spinner with gradient -->
				<svg class="animate-spin h-16 w-16" viewBox="0 0 24 24">
					<defs>
						<linearGradient id="spinner-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
							<stop offset="0%" stop-color="#60A5FA" />
							<stop offset="100%" stop-color="#3B82F6" />
						</linearGradient>
					</defs>
					<circle 
						class="opacity-25" 
						cx="12" cy="12" r="10" 
						stroke="currentColor" 
						stroke-width="4"
						fill="none"
						stroke-dasharray="32"
						stroke-dashoffset="12"
						stroke-linecap="round"
					></circle>
					<path
						class="opacity-75"
						fill="url(#spinner-gradient)"
						d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
					></path>
				</svg>
				<p class="mt-4 text-center text-gray-600 dark:text-gray-400 animate-pulse">Loading vault data...</p>
			</div>
		</div>
	{:else if error}
		<Alert color="red" class="mb-4">
			<span class="font-medium">Error:</span> {error}
		</Alert>
	{:else}
		<Tabs style="underline" contentClass="p-4 mt-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
			<TabItem open={activeTab === 0} on:click={() => activeTab = 0}>
				<span slot="title" class="flex items-center gap-2">
					<ChartPieSolid class="w-5 h-5" />
					Overview
				</span>
				<div class="space-y-6">
					<!-- Refresh Button -->
					<div class="flex justify-end">
						<Button color="alternative" size="sm" on:click={loadData} disabled={loading}>
							{#if loading}
								<div class="flex items-center">
									<span class="animate-spin inline-block w-4 h-4 border-2 border-t-transparent border-primary-500 rounded-full mr-2"></span>
									<span>Loading...</span>
								</div>
							{:else}
								Refresh Data
							{/if}
						</Button>
					</div>
					
					{#if balanceData}
						{#if balanceData.error}
							<div class="p-4 bg-yellow-50 dark:bg-yellow-900 rounded-lg border border-yellow-200 dark:border-yellow-700">
								<h3 class="text-lg font-semibold text-yellow-800 dark:text-yellow-200 mb-2">Balance Information</h3>
								<p class="text-yellow-700 dark:text-yellow-300">{balanceData.error}</p>
								{#if balanceData.principalId}
									<p class="text-sm text-yellow-600 dark:text-yellow-400 mt-1">
										Principal: <span class="font-mono">{balanceData.principalId}</span>
									</p>
								{/if}
							</div>
						{:else}
							<BalanceCard 
								balance={balanceData.balance} 
								token={balanceData.token} 
								vaultStatus={vaultStatus} 
							/>
						{/if}
					{/if}
					
					{#if vaultStatus}
						<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
							<div class="bg-white dark:bg-gray-700 p-4 rounded-lg shadow">
								<div class="flex items-center gap-2 mb-2">
									<DollarOutline class="w-5 h-5 text-primary-600" />
									<h3 class="text-lg font-semibold">Total Supply</h3>
								</div>
								<p class="text-2xl font-bold">{formatCkBTC(vaultStatus.total_supply)}</p>
								<p class="text-sm text-gray-500 dark:text-gray-400">{vaultStatus.token} tokens</p>
							</div>
							
							<div class="bg-white dark:bg-gray-700 p-4 rounded-lg shadow">
								<div class="flex items-center gap-2 mb-2">
									<ChartOutline class="w-5 h-5 text-primary-600" />
									<h3 class="text-lg font-semibold">Accounts</h3>
								</div>
								<p class="text-2xl font-bold">{vaultStatus.accounts}</p>
								<p class="text-sm text-gray-500 dark:text-gray-400">Active accounts</p>
							</div>
							
							<div class="bg-white dark:bg-gray-700 p-4 rounded-lg shadow">
								<div class="flex items-center gap-2 mb-2">
									<ClockSolid class="w-5 h-5 text-primary-600" />
									<h3 class="text-lg font-semibold">Transactions</h3>
								</div>
								<p class="text-2xl font-bold">{totalTransactions}</p>
								<p class="text-sm text-gray-500 dark:text-gray-400">Total transactions</p>
							</div>
						</div>
					{/if}
				</div>
			</TabItem>
			
			<TabItem open={activeTab === 1} on:click={() => activeTab = 1}>
				<span slot="title" class="flex items-center gap-2">
					<PaperPlaneSolid class="w-5 h-5" />
					Transfer
				</span>
				<div class="space-y-4 max-w-md mx-auto">
					<h3 class="text-xl font-semibold mb-4">Transfer Tokens</h3>
					
					{#if transferSuccess}
						<Alert color="green" class="mb-4">
							Transfer completed successfully!
						</Alert>
					{/if}
					
					{#if transferError}
						<Alert color="red" class="mb-4">
							<span class="font-medium">Error:</span> {transferError}
						</Alert>
					{/if}
					
					<form on:submit|preventDefault={transferTokens} class="space-y-4">
						<div>
							<label for="recipient" class="block mb-2 text-sm font-medium text-gray-900 dark:text-white">
								Recipient Address (Principal ID)
							</label>
							<Input 
								id="recipient" 
								bind:value={transferRecipient} 
								placeholder="Enter recipient principal ID" 
								required
							/>
						</div>
						
						<div>
							<label for="amount" class="block mb-2 text-sm font-medium text-gray-900 dark:text-white">
								Amount
							</label>
							<Input 
								id="amount" 
								type="number" 
								bind:value={transferAmount} 
								placeholder="0.00" 
								min="0.01" 
								step="0.01" 
								required
							/>
						</div>
						
						<div>
							<label for="memo" class="block mb-2 text-sm font-medium text-gray-900 dark:text-white">
								Memo (Optional)
							</label>
							<Input 
								id="memo" 
								bind:value={transferMemo} 
								placeholder="Add a note about this transfer"
							/>
						</div>
						
						<Button type="submit" color="primary" class="w-full" disabled={transferLoading}>
							{#if transferLoading}
								<Spinner class="mr-2" size="4" />
							{/if}
							Transfer Tokens
						</Button>
					</form>
				</div>
			</TabItem>
			
			<TabItem open={activeTab === 2} on:click={() => activeTab = 2}>
				<span slot="title" class="flex items-center gap-2">
					<ClockSolid class="w-5 h-5" />
					Transactions
				</span>
				<div class="space-y-4">
					<div class="flex justify-between items-center mb-4">
						<h3 class="text-xl font-semibold">Transaction History</h3>
						<Button color="alternative" size="sm" on:click={getTransactions} disabled={loading}>
							{#if loading}
								<div class="flex items-center">
									<span class="animate-spin inline-block w-4 h-4 border-2 border-t-transparent border-primary-500 rounded-full mr-2"></span>
									<span>Loading...</span>
								</div>
							{:else}
								Refresh
							{/if}
						</Button>
					</div>
					
					<TransactionsList {transactions} principalId={userPrincipalId} />
				</div>
			</TabItem>

			<!-- New Accounts Tab -->
			<TabItem open={activeTab === 3} on:click={() => activeTab = 3}>
				<span slot="title" class="flex items-center gap-2">
					<UsersSolid class="w-5 h-5" />
					Accounts
				</span>
				<div class="space-y-4">
					<div class="flex justify-between items-center mb-4">
						<h3 class="text-xl font-semibold">Account Balances</h3>
						<Button color="alternative" size="sm" on:click={getVaultStatus} disabled={loading}>
							{#if loading}
								<div class="flex items-center">
									<span class="animate-spin inline-block w-4 h-4 border-2 border-t-transparent border-primary-500 rounded-full mr-2"></span>
									<span>Loading...</span>
								</div>
							{:else}
								Refresh
							{/if}
						</Button>
					</div>
					
					{#if accounts.length === 0}
						<div class="text-center py-8 text-gray-500 dark:text-gray-400">
							No accounts found.
						</div>
					{:else}
						<Table striped={true}>
							<TableHead>
								<TableHeadCell>Principal ID</TableHeadCell>
								<TableHeadCell>Balance (ckBTC)</TableHeadCell>
							</TableHead>
							<TableBody>
								{#each accounts as account}
									<TableBodyRow>
										<TableBodyCell>
											<div class="font-mono text-sm truncate max-w-xs" title={account.principal_id}>
												{account.principal_id}
											</div>
										</TableBodyCell>
										<TableBodyCell>
											<div class="font-medium">
												{formatCkBTC(account.amount)}
											</div>
										</TableBodyCell>
									</TableBodyRow>
								{/each}
							</TableBody>
						</Table>
					{/if}
				</div>
			</TabItem>
		</Tabs>
	{/if}
</Card>
