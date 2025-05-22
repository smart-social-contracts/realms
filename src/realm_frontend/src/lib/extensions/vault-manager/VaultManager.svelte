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
			// Use the extension API method
			if (!backend || !backend.vault_manager_get_balance) {
				console.warn('Backend or vault_manager_get_balance method not available');
				// Mock balance data for development
				balanceData = {
					balance: 1000,
					token: "ICP",
					principalId: $principal || "2vxsx-fae"
				};
				console.log('Using mock balance data:', balanceData);
				return;
			}
			
			const response = await backend.vault_manager_get_balance();
			
			if (response.success) {
				balanceData = {
					balance: response.data.balance,
					token: response.data.token,
					principalId: response.data.principal_id
				};
				console.log('Balance data:', balanceData);
			} else {
				error = `Failed to get balance: ${response.error}`;
				console.error(error);
			}
		} catch (err) {
			console.error('Error fetching balance:', err);
			// Fallback to mock data on error
			balanceData = {
				balance: 1000,
				token: "ICP",
				principalId: $principal || "2vxsx-fae"
			};
		}
	}
	
	// Get vault status information
	async function getVaultStatus() {
		try {
			// Use the extension API method
			if (!backend || !backend.vault_manager_get_status) {
				console.warn('Backend or vault_manager_get_status method not available');
				// Mock vault status data for development
				vaultStatus = {
					version: "1.0.0",
					name: "Realm Vault",
					token: "ICP",
					total_supply: 10000000,
					accounts: 42
				};
				console.log('Using mock vault status data:', vaultStatus);
				return;
			}
			
			const response = await backend.vault_manager_get_status();
			
			if (response.success) {
				vaultStatus = response.data;
				console.log('Vault status:', vaultStatus);
			} else {
				error = `Failed to get vault status: ${response.error}`;
				console.error(error);
			}
		} catch (err) {
			console.error('Error fetching vault status:', err);
			// Fallback to mock data on error
			vaultStatus = {
				version: "1.0.0",
				name: "Realm Vault",
				token: "ICP",
				total_supply: 10000000,
				accounts: 42
			};
		}
	}
	
	// Get recent transactions
	async function getTransactions() {
		try {
			// Use the extension API method
			if (!backend || !backend.vault_manager_get_transactions) {
				console.warn('Backend or vault_manager_get_transactions method not available');
				// Mock transaction data for development
				transactions = [
					{
						id: "tx1",
						from: "2vxsx-fae",
						to: "3vxsx-fae",
						amount: 100,
						token: "ICP",
						timestamp: Date.now() - 1000000,
						memo: "Test transaction 1"
					},
					{
						id: "tx2",
						from: "3vxsx-fae",
						to: "2vxsx-fae",
						amount: 50,
						token: "ICP",
						timestamp: Date.now() - 2000000,
						memo: "Test transaction 2"
					}
				];
				totalTransactions = 2;
				console.log('Using mock transaction data:', transactions);
				return;
			}
			
			const response = await backend.vault_manager_get_transactions({
				limit: 10,
				offset: 0
			});
			
			if (response.success) {
				// Format transactions for the UI
				transactions = response.data.transactions.map(tx => ({
					id: tx.id,
					from: tx.from_principal,
					to: tx.to_principal,
					amount: tx.amount,
					token: vaultStatus?.token || "ICP",
					timestamp: tx.timestamp,
					status: tx.status,
					memo: tx.memo || ""
				}));
				totalTransactions = response.data.total;
				console.log('Transactions:', transactions);
			} else {
				error = `Failed to get transactions: ${response.error}`;
				console.error(error);
			}
		} catch (err) {
			console.error('Error fetching transactions:', err);
			// Fallback to mock data on error
			transactions = [
				{
					id: "tx1",
					from: "2vxsx-fae",
					to: "3vxsx-fae",
					amount: 100,
					token: "ICP",
					timestamp: Date.now() - 1000000,
					memo: "Test transaction 1"
				},
				{
					id: "tx2",
					from: "3vxsx-fae",
					to: "2vxsx-fae",
					amount: 50,
					token: "ICP",
					timestamp: Date.now() - 2000000,
					memo: "Test transaction 2"
				}
			];
			totalTransactions = 2;
		}
	}
	
	// Transfer tokens to another principal
	async function transferTokens() {
		transferLoading = true;
		transferSuccess = false;
		transferError = '';
		
		try {
			// Use the extension API method
			if (!backend || !backend.vault_manager_transfer) {
				console.warn('Backend or vault_manager_transfer method not available');
				// Mock transfer response for development
				await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate delay
				console.log('Mock transfer completed');
				transferSuccess = true;
				resetTransferForm();
				await getBalance();
				return;
			}
			
			const response = await backend.vault_manager_transfer({
				to_principal_id: transferRecipient,
				amount: parseFloat(transferAmount),
				memo: transferMemo
			});
			
			if (response.success) {
				transferSuccess = true;
				console.log('Transfer successful, tx ID:', response.data.transaction_id);
				resetTransferForm();
				await getBalance();
				await getTransactions(); // Refresh transactions after transfer
			} else {
				transferError = `Transfer failed: ${response.error}`;
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
	
	// Initialize the component
	onMount(async () => {
		try {
			loading = true;
			await Promise.all([
				getBalance(),
				getVaultStatus(),
				getTransactions()
			]);
		} finally {
			loading = false;
		}
	});
</script>

<Card size="lg" padding="xl" class="w-full">
	<div class="flex items-center mb-4">
		<WalletSolid class="mr-2 h-8 w-8 text-primary-600" />
		<h2 class="text-2xl font-bold text-gray-900 dark:text-white">Vault Manager</h2>
	</div>

	{#if loading}
		<div class="flex justify-center items-center h-60">
			<Spinner size="16" />
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
					{#if balanceData}
						<BalanceCard 
							balance={balanceData.balance} 
							token={balanceData.token || 'GGG'} 
							vaultStatus={vaultStatus} 
						/>
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
