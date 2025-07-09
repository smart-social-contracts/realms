<script>
	import { Card, Button, Table, TableHead, TableHeadCell, TableBody, TableBodyRow, TableBodyCell, Badge } from 'flowbite-svelte';
	import { DollarOutline, ArrowUpOutline, ArrowDownOutline } from 'flowbite-svelte-icons';
	import { mockVaultData, mockTransactions } from '$lib/dummy-data/extensions';

	function formatNumber(num, decimals = 2) {
		return new Intl.NumberFormat('en-US', {
			minimumFractionDigits: decimals,
			maximumFractionDigits: decimals
		}).format(num);
	}

	$: formattedBalance = formatNumber(mockVaultData.balance / 100000000, 8);
	let priceUSD = 42500;
	$: balanceUSD = (mockVaultData.balance / 100000000) * priceUSD;

	function formatDate(dateStr) {
		return new Date(dateStr).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function getTransactionIcon(type) {
		return type === 'deposit' ? ArrowDownOutline : ArrowUpOutline;
	}

	function getTransactionColor(type) {
		return type === 'deposit' ? 'text-green-600' : 'text-red-600';
	}
</script>

<div class="py-6">
	<div class="mb-8">
		<h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-200">Vault Manager</h1>
		<p class="text-gray-600 dark:text-gray-400">Manage your cryptocurrency vault and transactions</p>
	</div>

	<div class="grid gap-6 mb-8 md:grid-cols-2">
		<div class="bg-gradient-to-r from-purple-500 to-purple-700 rounded-xl text-white p-6 shadow-lg">
			<div class="flex justify-between items-start">
				<div>
					<h3 class="text-xl font-semibold mb-1">Your Balance</h3>
					<div class="flex items-baseline">
						<span class="text-3xl font-bold">{formattedBalance}</span>
						<span class="ml-2 text-lg">{mockVaultData.token}</span>
					</div>
					<div class="text-purple-100 mt-1">
						≈ ${formatNumber(balanceUSD, 2)} USD
					</div>
				</div>
				<div class="bg-white/20 p-3 rounded-lg">
					<DollarOutline class="h-8 w-8 text-white" />
				</div>
			</div>
			
			<div class="mt-6 grid grid-cols-2 gap-4">
				<div class="bg-white/10 p-3 rounded-lg">
					<h4 class="text-sm font-medium text-purple-100">Principal ID</h4>
					<p class="text-sm font-mono truncate mt-1 text-white" title={mockVaultData.vaultStatus.principalId}>
						{mockVaultData.vaultStatus.principalId.substring(0, 10)}...
					</p>
				</div>
				<div class="bg-white/10 p-3 rounded-lg">
					<h4 class="text-sm font-medium text-purple-100">Vault</h4>
					<p class="text-sm mt-1 flex items-center">
						<span class="inline-block w-2 h-2 bg-green-400 rounded-full mr-2"></span>
						{mockVaultData.vaultStatus.name}
					</p>
				</div>
			</div>
		</div>

		<Card>
			<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-200 mb-4">Quick Actions</h3>
			<div class="space-y-3">
				<Button class="w-full justify-center" color="green">
					<ArrowDownOutline class="w-4 h-4 mr-2" />
					Deposit Funds
				</Button>
				<Button class="w-full justify-center" color="red">
					<ArrowUpOutline class="w-4 h-4 mr-2" />
					Withdraw Funds
				</Button>
				<Button class="w-full justify-center" color="blue">
					<DollarOutline class="w-4 h-4 mr-2" />
					Transfer Funds
				</Button>
			</div>
		</Card>
	</div>

	<Card>
		<div class="flex items-center justify-between mb-4">
			<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-200">Recent Transactions</h3>
			<Button size="xs">View All</Button>
		</div>
		
		<Table striped={true}>
			<TableHead>
				<TableHeadCell>Type</TableHeadCell>
				<TableHeadCell>Amount</TableHeadCell>
				<TableHeadCell>Date</TableHeadCell>
				<TableHeadCell>Status</TableHeadCell>
				<TableHeadCell>Hash</TableHeadCell>
			</TableHead>
			<TableBody>
				{#each mockTransactions as transaction}
					<TableBodyRow>
						<TableBodyCell>
							<div class="flex items-center">
								<svelte:component 
									this={getTransactionIcon(transaction.type)} 
									class="w-4 h-4 mr-2 {getTransactionColor(transaction.type)}" 
								/>
								<span class="capitalize">{transaction.type}</span>
							</div>
						</TableBodyCell>
						<TableBodyCell>
							<span class={getTransactionColor(transaction.type)}>
								{transaction.type === 'deposit' ? '+' : '-'}{formatNumber(transaction.amount / 100000000, 8)} {transaction.token}
							</span>
						</TableBodyCell>
						<TableBodyCell>{formatDate(transaction.timestamp)}</TableBodyCell>
						<TableBodyCell>
							<Badge color="green">{transaction.status}</Badge>
						</TableBodyCell>
						<TableBodyCell>
							<span class="font-mono text-sm">{transaction.hash.substring(0, 12)}...</span>
						</TableBodyCell>
					</TableBodyRow>
				{/each}
			</TableBody>
		</Table>
	</Card>
</div>
