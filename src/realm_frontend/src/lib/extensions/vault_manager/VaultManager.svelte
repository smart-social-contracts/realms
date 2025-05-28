<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, Tabs, TabItem, Spinner, Button, Input, Alert } from 'flowbite-svelte';
	import { ChartPieSolid, ClockSolid, WalletSolid,
		ChartOutline, PaperPlaneSolid, DollarOutline } from 'flowbite-svelte-icons';
	import { principal } from '$lib/stores/auth';
	import { formatNumber } from '$lib/utils';
	import TransactionsList from './TransactionsList.svelte';
	import BalanceCard from './BalanceCard.svelte';
	
	// Import backend directly without using await in top-level
	import { backend } from '$lib/canisters';
	
	// Component state
	let loading = true;
	let error = '';
	let activeTab = 0;
	let balanceData = null;
	let vaultStatus = null;
	let transactions = [];
	let totalTransactions = 0;
	
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
	
	// Get vault balance for current user
	async function getBalance() {
		try {
			// Use the extension_call API method with proper arguments including vault_canister_id
			const response = await backend.extension_call({
				extension_name: "vault_manager",
				function_name: "get_balance",
				args: JSON.stringify({ 
					principal_id: userPrincipalId,
					vault_canister_id: vaultCanisterId
				})
			});
			
			console.log('Balance response:', response);
			
			if (response.success) {
				// Parse the JSON response
				const data = JSON.parse(response.response);
				console.log('Parsed balance data:', data);
				
				if (data.success) {
					// Handle successful balance response
					balanceData = {
						balance: data.data.amount || 0,
						token: "GGG",
						principalId: userPrincipalId
					};
					console.log('Balance data set:', balanceData);
				} else {
					// Handle vault error (e.g., balance not found)
					console.log('Vault returned error:', data.error);
					balanceData = {
						balance: 0,
						token: "GGG", 
						principalId: userPrincipalId,
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
			// Use the extension_call API method including vault_canister_id
			const response = await backend.extension_call({
				extension_name: "vault_manager",
				function_name: "get_status",
				args: JSON.stringify({ vault_canister_id: vaultCanisterId })
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
						token: "GGG",
						total_supply: stats.app_data?.sync_tx_id || 0,
						accounts: stats.balances?.length || 0,
						admin_principal: stats.app_data?.admin_principal || "Unknown",
						sync_status: stats.app_data?.sync_status || "Unknown"
					};
					console.log('Vault status set:', vaultStatus);
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
			// Use the extension_call API method to get transactions directly from the vault canister
			const response = await backend.extension_call({
				extension_name: "vault_manager",
				function_name: "get_transactions",
				args: JSON.stringify({ 
					principal_id: vaultCanisterId, // Use the vault canister ID directly as the principal
					vault_canister_id: vaultCanisterId
				})
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
						
						// Determine if this is an incoming or outgoing transaction
						const isIncoming = !tx.amount.startsWith("-");
						const amount = isIncoming ? tx.amount : tx.amount.substring(1); // Remove minus sign if outgoing
						
						return {
							id: tx.id,
							from_principal: isIncoming ? "system" : userPrincipalId,
							to_principal: isIncoming ? userPrincipalId : "recipient",
							amount: parseInt(amount),
							token: "GGG",
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
			// Use the extension_call API method including vault_canister_id
			const response = await backend.extension_call({
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
		<h2 class="text-2xl font-bold text-gray-900 dark:text-white">Vault Manager</h2>
	</div>

	<!-- Configuration Section -->
	<div class="vault-configuration mb-6">
		<h3 class="text-xl font-bold mb-4">Vault Configuration</h3>
		
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
		<!-- Enhanced loading indicator instead of big gray circle -->
		<div class="flex flex-col items-center justify-center p-12">
			<Spinner size="xl" color="blue" />
			<p class="mt-4 text-gray-600 dark:text-gray-400">Loading vault data...</p>
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
								<Spinner class="mr-2" size="4" />
							{/if}
							Refresh Data
						</Button>
					</div>
					
					{#if balanceData}
						{#if balanceData.error}
							<div class="p-4 bg-yellow-50 dark:bg-yellow-900 rounded-lg border border-yellow-200 dark:border-yellow-700">
								<h3 class="text-lg font-semibold text-yellow-800 dark:text-yellow-200 mb-2">Balance Information</h3>
								<p class="text-yellow-700 dark:text-yellow-300">{balanceData.error}</p>
								<p class="text-sm text-yellow-600 dark:text-yellow-400 mt-1">
									Principal: <span class="font-mono">{balanceData.principalId}</span>
								</p>
							</div>
						{:else}
							<BalanceCard 
								balance={balanceData.balance} 
								token={balanceData.token || 'GGG'} 
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
								<p class="text-2xl font-bold">{formatNumber(vaultStatus.total_supply)}</p>
								<p class="text-sm text-gray-500 dark:text-gray-400">{vaultStatus.token || 'GGG'} tokens</p>
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
				<div>
					<h3 class="text-xl font-semibold mb-4">Transaction History</h3>
					<TransactionsList {transactions} principalId={balanceData?.principalId} />
				</div>
			</TabItem>
		</Tabs>
	{/if}
</Card>
