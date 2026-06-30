<!-- Act-on-behalf context switcher (Power of Attorney). -->
<script lang="ts">
	import { IconUserShield } from '@tabler/icons-svelte';
	import { onMount } from 'svelte';
	import { backend } from '$lib/canisters.js';
	import { isAuthenticated } from '$lib/stores/auth';
	import {
		actingOnBehalfOf,
		activeDelegationsAsDelegate,
		delegationsAsDelegate,
		loadDelegations,
		setActingOnBehalfOf,
		clearActingContext
	} from '$lib/stores/delegation.js';

	let loading = $state(false);

	const active = $derived(activeDelegationsAsDelegate($delegationsAsDelegate));
	const visible = $derived($isAuthenticated && active.length > 0);
	const selected = $derived($actingOnBehalfOf || '');

	onMount(async () => {
		if ($isAuthenticated) {
			loading = true;
			await loadDelegations(backend);
			loading = false;
		}
	});

	function labelFor(grantor: string) {
		const d = active.find((x) => x.grantor === grantor);
		return d?.label || `${grantor.slice(0, 8)}…${grantor.slice(-6)}`;
	}

	function onChange(event: Event) {
		const value = (event.currentTarget as HTMLSelectElement).value;
		if (!value) clearActingContext();
		else setActingOnBehalfOf(value);
	}
</script>

{#if visible}
	<div
		class="inline-flex items-center gap-1.5 rounded-lg border border-blue-200 bg-blue-50 px-2 py-1"
		title="Act on behalf of another member"
	>
		<IconUserShield size={18} class="text-blue-600" />
		<select
			value={selected}
			onchange={onChange}
			disabled={loading}
			aria-label="Acting on behalf of"
			class="max-w-[11rem] cursor-pointer truncate border-0 bg-transparent p-0 pr-5 text-sm font-medium text-blue-900 focus:outline-none focus:ring-0"
		>
			<option value="">Myself</option>
			{#each active as d (d.id)}
				<option value={d.grantor}>{labelFor(d.grantor)}</option>
			{/each}
		</select>
	</div>
{/if}
