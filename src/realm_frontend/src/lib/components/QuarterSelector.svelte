<script>
	import { onMount } from 'svelte';
	import { realmInfo } from '$lib/stores/realmInfo';
	import { activeQuarterId } from '$lib/stores/quarters';
	import { setActiveQuarter } from '$lib/canisters';

	let quarters = [];
	let selectedId = null;
	let open = false;
	let homeQuarterId = null;

	// React to realmInfo changes to get quarters list
	$: quarters = $realmInfo?.quarters || [];
	$: hasQuarters = quarters.length > 0;

	// Sync local selection with store
	$: selectedId = $activeQuarterId;

	// Read cached home quarter for guest/home tagging
	onMount(() => {
		if (typeof localStorage !== 'undefined') {
			homeQuarterId = localStorage.getItem('home_quarter');
		}
	});

	function selectQuarter(quarterId) {
		if (quarterId === selectedId) {
			open = false;
			return;
		}
		activeQuarterId.set(quarterId);
		setActiveQuarter(quarterId);
		open = false;
	}

	function selectMainRealm() {
		activeQuarterId.set(null);
		setActiveQuarter(null);
		open = false;
	}

	function toggleDropdown() {
		open = !open;
	}

	// Close dropdown on outside click
	function handleClickOutside(event) {
		const el = event.target.closest('.quarter-selector');
		if (!el) open = false;
	}

	onMount(() => {
		document.addEventListener('click', handleClickOutside);
		return () => document.removeEventListener('click', handleClickOutside);
	});

	$: selectedLabel = (() => {
		if (!selectedId) return 'Main Realm';
		const q = quarters.find(q => q.canister_id === selectedId);
		return q ? q.name : selectedId.slice(0, 8) + '...';
	})();
</script>

{#if hasQuarters}
	<div class="quarter-selector relative inline-block">
		<button
			on:click={toggleDropdown}
			class="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors"
			title="Switch quarter"
		>
			<span class="text-xs">🏘️</span>
			<span class="max-w-[120px] truncate">{selectedLabel}</span>
			<svg class="w-3 h-3 text-gray-500 transition-transform {open ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/>
			</svg>
		</button>

		{#if open}
			<div class="absolute right-0 top-full mt-1 w-56 bg-white border border-gray-200 rounded-lg shadow-lg z-50 py-1">
				<!-- Main Realm option -->
				<button
					on:click={selectMainRealm}
					class="w-full text-left px-4 py-2 text-sm hover:bg-gray-50 flex items-center gap-2 {!selectedId ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-700'}"
				>
					<span class="text-xs">🏛️</span>
					Main Realm
					{#if !selectedId}
						<span class="ml-auto text-blue-500 text-xs">✓</span>
					{/if}
				</button>

				<div class="border-t border-gray-100 my-1"></div>

				<!-- Quarter options -->
				{#each quarters as quarter}
					<button
						on:click={() => selectQuarter(quarter.canister_id)}
						class="w-full text-left px-4 py-2 text-sm hover:bg-gray-50 flex items-center gap-2 {selectedId === quarter.canister_id ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-700'}"
					>
						<span class="text-xs">{quarter.canister_id === homeQuarterId ? '�' : '�🏘️'}</span>
						<span class="flex-1 truncate">{quarter.name}</span>
						{#if quarter.canister_id === homeQuarterId}
							<span class="text-xs text-green-600 font-medium">Home</span>
						{:else if homeQuarterId}
							<span class="text-xs text-gray-400 italic">Guest</span>
						{/if}
						<span class="text-xs text-gray-400">{quarter.population || 0}</span>
						{#if selectedId === quarter.canister_id}
							<span class="text-blue-500 text-xs">✓</span>
						{/if}
					</button>
				{/each}
			</div>
		{/if}
	</div>
{/if}
