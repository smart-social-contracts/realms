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
	
	// Canister IDs - will be loaded from declarations
	let backendCanisterId = "";
	let vaultCanisterIdFromDeclarations = "";
	
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
	let vaultCanisterId = ""; // Will be set from declarations or demo mode
	
	// Demo vault data - populated with realistic ckBTC values
	let demoMode = false;
	let demoBalanceData = {
		balance: 250000000, // 2.5 ckBTC (in satoshis)
		token: "ckBTC",
		principalId: "rdmx6-jaaaa-aaaah-qcaiq-cai"
	};
	
	let demoVaultStatus = {
		version: "1.2.3",
		name: "Realms ckBTC Vault",
		token: "ckBTC",
		total_supply: 1500000000000, // 15,000 ckBTC total supply
		accounts: 47,
		admin_principal: "rrkah-fqaaa-aaaah-qcuaq-cai",
		sync_status: "Synced"
	};
	
	let demoTransactions = [
		{
			id: "tx_001_demo",
			from_principal: "2vxsx-fae",
			to_principal: "rdmx6-jaaaa-aaaah-qcaiq-cai",
			amount: 50000000, // 0.5 ckBTC
			token: "ckBTC",
			timestamp: Date.now() - 3600000, // 1 hour ago
			status: "completed"
		},
		{
			id: "tx_002_demo", 
			from_principal: "rdmx6-jaaaa-aaaah-qcaiq-cai",
			to_principal: "rrkah-fqaaa-aaaah-qcuaq-cai",
			amount: 25000000, // 0.25 ckBTC
			token: "ckBTC",
			timestamp: Date.now() - 7200000, // 2 hours ago
			status: "completed"
		},
		{
			id: "tx_003_demo",
			from_principal: "be2us-64aaa-aaaah-qabeq-cai",
			to_principal: "rdmx6-jaaaa-aaaah-qcaiq-cai", 
			amount: 100000000, // 1.0 ckBTC
			token: "ckBTC",
			timestamp: Date.now() - 14400000, // 4 hours ago
			status: "completed"
		},
		{
			id: "tx_004_demo",
			from_principal: "rdmx6-jaaaa-aaaah-qcaiq-cai",
			to_principal: "suaf3-haaaa-aaaah-qaaya-cai",
			amount: 75000000, // 0.75 ckBTC
			token: "ckBTC", 
			timestamp: Date.now() - 21600000, // 6 hours ago
			status: "completed"
		},
		{
			id: "tx_005_demo",
			from_principal: "qjdve-lqaaa-aaaah-qcvbq-cai",
			to_principal: "rdmx6-jaaaa-aaaah-qcaiq-cai",
			amount: 200000000, // 2.0 ckBTC
			token: "ckBTC",
			timestamp: Date.now() - 86400000, // 1 day ago
			status: "completed"
		}
	];
	
	let demoAccounts = [
		{
			principal_id: "rdmx6-jaaaa-aaaah-qcaiq-cai",
			amount: 250000000 // 2.5 ckBTC
		},
		{
			principal_id: "rrkah-fqaaa-aaaah-qcuaq-cai", 
			amount: 500000000 // 5.0 ckBTC
		},
		{
			principal_id: "be2us-64aaa-aaaah-qabeq-cai",
			amount: 150000000 // 1.5 ckBTC
		},
		{
			principal_id: "suaf3-haaaa-aaaah-qaaya-cai",
			amount: 300000000 // 3.0 ckBTC
		},
		{
			principal_id: "qjdve-lqaaa-aaaah-qcvbq-cai",
			amount: 750000000 // 7.5 ckBTC
		},
		{
			principal_id: "2vxsx-fae",
			amount: 100000000 // 1.0 ckBTC
		}
	];
	
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
		if (demoMode) {
			// Use demo data
			await new Promise(resolve => setTimeout(resolve, 500));
			balanceData = { ...demoBalanceData };
			return;
		}
		
		try {
			// Prepare call parameters
			const callParams = { 
				principal_id: backendCanisterId, // Use the vault canister ID as the principal, same as CLI example
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
		if (demoMode) {
			// Use demo data
			await new Promise(resolve => setTimeout(resolve, 500));
			vaultStatus = { ...demoVaultStatus };
			accounts = [...demoAccounts];
			return;
		}
		
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
		if (demoMode) {
			// Use demo data
			await new Promise(resolve => setTimeout(resolve, 500));
			transactions = [...demoTransactions];
			totalTransactions = demoTransactions.length;
			return;
		}
		
		try {
			// Prepare call parameters - using backend canister as the principal to query
			const callParams = { 
				principal_id: backendCanisterId,
				vault_canister_id: vaultCanisterId
			};
			
			console.log('Calling get_transactions with parameters:', callParams);
			
			// Call the refactored get_transactions endpoint
			const response = await backend.extension_async_call({
				extension_name: "vault_manager",
				function_name: "get_transactions",
				args: JSON.stringify(callParams)
			});
			
			console.log('Transactions response:', response);
			
			if (response.success) {
				const data = JSON.parse(response.response);
				console.log('Parsed transactions data:', data);
				
				if (data.success && data.data && data.data.Transactions && Array.isArray(data.data.Transactions)) {
					// Map the simplified transaction format from backend
					// Backend returns: [{id: int, amount: int, timestamp: int}, ...]
					transactions = data.data.Transactions.map((tx) => {
						// Convert nanoseconds to milliseconds
						const timestamp = parseInt(tx.timestamp) / 1000000;
						
						// Determine transaction direction based on amount sign
						const amount = parseInt(tx.amount) || 0;
						const isIncoming = amount > 0;
						const absoluteAmount = Math.abs(amount);
						
						return {
							id: String(tx.id) || "unknown",
							from_principal: isIncoming ? "external" : vaultCanisterId,
							to_principal: isIncoming ? vaultCanisterId : "external",
							amount: absoluteAmount,
							token: "ckBTC",
							timestamp: timestamp,
							status: "completed"
						};
					});
					totalTransactions = transactions.length;
					console.log(`Loaded ${transactions.length} transactions`);
				} else {
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
		
		try {
			if (demoMode) {
				// Use demo data for development/testing
				// Set demo vault canister ID
				vaultCanisterId = "aaaa-aa";
				await loadDemoData();
			} else {
				// Use canister IDs from declarations
				if (!vaultCanisterId || !backendCanisterId) {
					error = 'Canister IDs not loaded from declarations. Please refresh the page.';
					loading = false;
					return;
				}
				
				userPrincipalId = $principal || ""; // Always use authenticated principal
				
				// Run all data fetching in parallel
				await Promise.all([getBalance(), getVaultStatus(), getTransactions()]);
			}
			error = ''; // Clear any previous errors if successful
		} catch (err) {
			console.error('Error loading data:', err);
			error = `Error loading data: ${err.message || err}`;
		} finally {
			loading = false;
		}
	}
	
	// Load demo data with simulated delay
	async function loadDemoData() {
		// Simulate network delay
		await new Promise(resolve => setTimeout(resolve, 1000));
		
		// Set demo data
		balanceData = { ...demoBalanceData };
		vaultStatus = { ...demoVaultStatus };
		transactions = [...demoTransactions];
		totalTransactions = demoTransactions.length;
		accounts = [...demoAccounts];
		
		console.log('Demo data loaded:', {
			balanceData,
			vaultStatus,
			transactions: transactions.length,
			accounts: accounts.length
		});
	}
	
	// Initialize the component
	onMount(async () => {
		// Load canister IDs from declarations
		try {
			const realmBackendModule = await import('declarations/realm_backend');
			backendCanisterId = realmBackendModule.canisterId;
			console.log('Loaded realm_backend canister ID:', backendCanisterId);
			
			// Load vault canister ID from backend
			try {
				const response = await backend.extension_sync_call({
					extension_name: "vault_manager",
					function_name: "get_vault_canister_id",
					args: "{}"
				});
				
				console.log('Vault canister ID response:', response);
				
				if (response.success) {
					const data = JSON.parse(response.response);
					if (data.success && data.data && data.data.canister_id) {
						const vaultId = data.data.canister_id;
						vaultCanisterIdFromDeclarations = vaultId;
						vaultCanisterId = vaultId;
						console.log('Loaded vault canister ID from backend:', vaultId);
					} else {
						console.error('Invalid vault canister ID response:', data);
					}
				} else {
					console.error('Failed to get vault canister ID:', response);
				}
			} catch (e) {
				console.error('Error loading vault canister ID from backend:', e);
			}
		} catch (e) {
			console.error('Error loading canister IDs from declarations:', e);
		}
		
		// Auto-load data if we have canister IDs (either demo mode or from declarations)
		if (demoMode || (backendCanisterId && vaultCanisterId)) {
			await loadData();
		} else {
			loading = false; // Stop loading state if canister IDs couldn't be loaded
		}
	});
</script>

<div class="w-full h-full p-6 bg-white dark:bg-gray-900">
	<div class="flex items-center mb-4">
		<WalletSolid class="mr-2 h-8 w-8 text-primary-600" />
		<h2 class="text-2xl font-bold text-gray-900 dark:text-white">{$_('extensions.vault_manager.title')}</h2>
	</div>

	<!-- Configuration Section -->
	<div class="vault-configuration mb-6">
		<h3 class="text-xl font-bold mb-4">{$_('extensions.vault_manager.configuration.title')}</h3>
		
		<!-- Demo Mode Toggle -->
		<div class="mb-4 p-4 bg-blue-50 dark:bg-blue-900 rounded-lg border border-blue-200 dark:border-blue-700">
			<div class="flex items-center justify-between mb-2">
				<div class="flex items-center">
					<span class="text-sm font-medium text-blue-800 dark:text-blue-200">Demo Mode</span>
					{#if demoMode}
						<span class="ml-2 px-2 py-1 text-xs bg-blue-600 text-white rounded-full">Active</span>
					{/if}
				</div>
				<Button 
					size="xs" 
					color={demoMode ? "red" : "blue"} 
					on:click={() => { 
						demoMode = !demoMode; 
						if (demoMode) {
							// Auto-load demo data when enabling demo mode
							loadData();
						} else {
							// Restore vault canister ID from declarations and reload
							vaultCanisterId = vaultCanisterIdFromDeclarations;
							loadData();
						}	
					}}
				>
					{demoMode ? "Disable Demo" : "Enable Demo"}
				</Button>
			</div>
			{#if demoMode}
				<p class="text-sm text-blue-700 dark:text-blue-300">
					Using demo data with realistic ckBTC vault information. Perfect for testing and demonstrations.
				</p>
			{:else}
				<p class="text-sm text-blue-700 dark:text-blue-300">
					Connected to vault canister: <span class="font-mono font-semibold">{vaultCanisterId || 'Loading...'}</span>
				</p>
			{/if}
		</div>
		
		<Button color="primary" on:click={loadData}>
			{#if loading}
				<div class="flex items-center">
					<Spinner class="mr-2" size="sm" color="white" />
					<span>Loading...</span>
				</div>
			{:else}
				<span>{demoMode ? "Load Demo Data" : "Load Vault"}</span>
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
					<!-- Demo Mode Indicator and Refresh Button -->
					<div class="flex justify-between items-center">
						{#if demoMode}
							<div class="flex items-center">
								<span class="px-3 py-1 text-sm bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded-full">
									📊 Demo Data Active
								</span>
							</div>
						{:else}
							<div></div>
						{/if}
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
						<div class="flex items-center gap-3">
							<h3 class="text-xl font-semibold">Transaction History</h3>
							{#if demoMode}
								<span class="px-3 py-1 text-xs bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 rounded-full">
									📊 Demo Data
								</span>
							{/if}
						</div>
						<Button color="alternative" size="sm" on:click={getTransactions} disabled={loading || demoMode}>
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
</div>
