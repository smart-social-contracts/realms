<script lang="ts">
	import { Card } from 'flowbite-svelte';
	import { DollarOutline } from 'flowbite-svelte-icons';
	import { formatNumber } from '$lib/utils';
	
	export let balance: number;
	export let token: string = 'GGG';
	export let vaultStatus: any = null;
	
	// Format balance for display (assuming smallest unit is 1/100)
	$: formattedBalance = formatNumber(balance / 100);
	
	// Random price fluctuation for demo purposes (would use real price data in production)
	let priceUSD = Math.random() * 10 + 5; // Random price between $5-15
	$: balanceUSD = (balance / 100) * priceUSD;
</script>

<div class="bg-gradient-to-r from-primary-500 to-primary-700 rounded-xl text-white p-6 shadow-lg">
	<div class="flex justify-between items-start">
		<div>
			<h3 class="text-xl font-semibold mb-1">Your Balance</h3>
			<div class="flex items-baseline">
				<span class="text-3xl font-bold">{formattedBalance}</span>
				<span class="ml-2 text-lg">{token}</span>
			</div>
			<div class="text-primary-100 mt-1">
				≈ ${formatNumber(balanceUSD, 2)} USD
			</div>
		</div>
		<div class="bg-white/20 p-3 rounded-lg">
			<DollarOutline class="h-8 w-8 text-white" />
		</div>
	</div>
	
	<div class="mt-6 grid grid-cols-2 gap-4">
		<div class="bg-white/10 p-3 rounded-lg">
			<h4 class="text-sm font-medium text-primary-100">Principal ID</h4>
			<p class="text-sm font-mono truncate mt-1 text-white" title={vaultStatus?.principalId || 'Not available'}>
				{#if vaultStatus?.principalId}
					{vaultStatus.principalId.substring(0, 10)}...
				{:else}
					-
				{/if}
			</p>
		</div>
		<div class="bg-white/10 p-3 rounded-lg">
			<h4 class="text-sm font-medium text-primary-100">Vault</h4>
			<p class="text-sm mt-1 flex items-center">
				<span class="inline-block w-2 h-2 bg-green-400 rounded-full mr-2"></span>
				{vaultStatus?.name || 'Connected'}
			</p>
		</div>
	</div>
</div>
