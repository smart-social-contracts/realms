<script lang="ts">
	import { actingOnBehalfOf, clearActingContext } from '$lib/stores/delegation.js';
	import { principal } from '$lib/stores/auth';

	const grantor = $derived($actingOnBehalfOf);
	const shortYou = $derived(
		$principal ? `${$principal.slice(0, 8)}…${$principal.slice(-6)}` : ''
	);
	const shortGrantor = $derived(
		grantor ? `${grantor.slice(0, 8)}…${grantor.slice(-6)}` : ''
	);
</script>

{#if grantor}
	<div
		class="border-b border-blue-200 bg-blue-50 px-4 py-2 text-sm text-blue-900 flex flex-wrap items-center justify-between gap-2"
		role="status"
	>
		<span>
			Acting on behalf of <strong>{shortGrantor}</strong>
			<span class="text-blue-700">· your identity {shortYou}</span>
		</span>
		<button
			type="button"
			class="rounded-md border border-blue-300 bg-white px-2 py-0.5 text-xs font-medium hover:bg-blue-100"
			onclick={() => clearActingContext()}
		>
			Stop acting
		</button>
	</div>
{/if}
