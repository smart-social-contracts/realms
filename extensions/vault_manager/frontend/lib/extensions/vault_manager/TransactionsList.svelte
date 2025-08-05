<script lang="ts">
	import { Table, TableBody, TableBodyCell, TableBodyRow, TableHead, TableHeadCell, Badge, Avatar } from 'flowbite-svelte';
	import { ArrowDownOutline, ArrowUpOutline } from 'flowbite-svelte-icons';
	import { formatNumber } from '$lib/utils';
	
	type Transaction = {
		id: string;
		from_principal: string;
		to_principal: string;
		amount: number;
		token: string;
		timestamp: number;
		memo?: string;
		status?: string;
	};
	
	export let transactions: Transaction[] = [];
	export let principalId: string | null = null;
	
	// Format timestamp to readable date/time
	function formatDate(timestamp: number): string {
		const date = new Date(timestamp);
		return date.toLocaleString();
	}
	
	// Determine if transaction is incoming or outgoing
	function getTransactionType(tx: Transaction): 'incoming' | 'outgoing' | 'unknown' {
		if (!principalId) return 'unknown';
		return tx.to_principal === principalId ? 'incoming' : 'outgoing';
	}
	
	// Format principal ID for display (truncate)
	function formatPrincipal(principal: string | null): string {
		if (!principal) return '-';
		return principal.length > 16 ? principal.substring(0, 8) + '...' + principal.substring(principal.length - 8) : principal;
	}
	
	// Get status badge color based on transaction status
	type BadgeColor = 'red' | 'yellow' | 'green' | 'dark' | 'blue' | 'indigo' | 'purple' | 'pink' | 'none';
	
	function getStatusColor(status?: string): BadgeColor {
		if (!status) return 'dark';
		switch (status.toLowerCase()) {
			case 'completed':
			case 'success':
				return 'green';
			case 'pending':
				return 'yellow';
			case 'failed':
				return 'red';
			default:
				return 'dark';
		}
	}
</script>

{#if transactions.length === 0}
	<div class="text-center py-8 text-gray-500 dark:text-gray-400">
		No transactions found.
	</div>
{:else}
	<Table striped={true} class="min-w-full">
		<TableHead>
			<TableHeadCell>Type</TableHeadCell>
			<TableHeadCell>Date</TableHeadCell>
			<TableHeadCell>From/To</TableHeadCell>
			<TableHeadCell>Amount</TableHeadCell>
			<TableHeadCell>Status</TableHeadCell>
			<TableHeadCell>Memo</TableHeadCell>
		</TableHead>
		<TableBody>
			{#each transactions as tx}
				{@const type = getTransactionType(tx)}
				<TableBodyRow>
					<TableBodyCell>
						<div class="flex items-center gap-2">
							{#if getTransactionType(tx) === 'incoming'}
								<div class="p-1.5 bg-green-100 dark:bg-green-900 rounded-full">
									<ArrowDownOutline class="w-4 h-4 text-green-500 dark:text-green-300" />
								</div>
								<span>From</span>
							{:else}
								<div class="p-1.5 bg-red-100 dark:bg-red-900 rounded-full">
									<ArrowUpOutline class="w-4 h-4 text-red-500 dark:text-red-300" />
								</div>
								<span>To</span>
							{/if}
						</div>
					</TableBodyCell>
					<TableBodyCell>
						{formatDate(tx.timestamp)}
					</TableBodyCell>
					<TableBodyCell>
						{#if type === 'incoming'}
							<div class="text-sm">
								<div class="font-medium">From</div>
								<div class="text-gray-500 dark:text-gray-400 font-mono text-xs">
									{formatPrincipal(tx.from_principal)}
								</div>
							</div>
						{:else}
							<div class="text-sm">
								<div class="font-medium">To</div>
								<div class="text-gray-500 dark:text-gray-400 font-mono text-xs">
									{formatPrincipal(tx.to_principal)}
								</div>
							</div>
						{/if}
					</TableBodyCell>
					<TableBodyCell>
						<div class="font-medium">
							{#if type === 'incoming'}
								<span class="text-green-600 dark:text-green-400">+{formatNumber(tx.amount / 100)}</span>
							{:else}
								<span class="text-blue-600 dark:text-blue-400">-{formatNumber(tx.amount / 100)}</span>
							{/if}
						</div>
					</TableBodyCell>
					<TableBodyCell>
						<Badge color={getStatusColor(tx.status || 'completed')}>{tx.status || 'Completed'}</Badge>
					</TableBodyCell>
					<TableBodyCell>
						<div class="text-sm text-gray-500 dark:text-gray-400 max-w-[150px] truncate" title={tx.memo || '-'}>
							{tx.memo || '-'}
						</div>
					</TableBodyCell>
				</TableBodyRow>
			{/each}
		</TableBody>
	</Table>
{/if}
