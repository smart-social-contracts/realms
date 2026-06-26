<!-- Admin-only quarter switcher (top bar).
     Lets an admin point this browser tab at a specific quarter (or the capital).
     It drives setActiveQuarter(), so every quarterBackend / ctx.backend call —
     including the realm_settings Quarters panel reads — targets the selection.
     Only shown to admins when the realm actually has more than one quarter.
     Quarter list comes from the realmInfo store (already fetched by the Navbar),
     so no extra backend call is needed here. -->
<script lang="ts">
	import { IconBuildingCommunity } from '@tabler/icons-svelte';
	import { _ } from 'svelte-i18n';
	import { userProfiles } from '$lib/stores/profiles';
	import { realmInfo } from '$lib/stores/realmInfo';
	import { activeQuarterId } from '$lib/stores/quarters';
	// @ts-ignore - canisters.js is untyped
	import { setActiveQuarter } from '$lib/canisters';

	interface QuarterOption {
		name: string;
		canister_id: string;
		population: number;
		status: string;
		index?: number;
		is_capital?: boolean;
	}

	const isAdmin = $derived(($userProfiles ?? []).includes('admin'));
	const quarters = $derived(($realmInfo.quarters ?? []) as QuarterOption[]);
	const capital = $derived(quarters.find((q) => q.is_capital));
	const capitalId = $derived(capital?.canister_id ?? '');
	// Show only to admins of an actual federation (more than just the capital).
	const visible = $derived(isAdmin && quarters.length > 1);
	const selected = $derived(($activeQuarterId as string | null) ?? capitalId);

	function onChange(event: Event) {
		const value = (event.currentTarget as HTMLSelectElement).value;
		const toCapital = value === capitalId || value === '';
		activeQuarterId.set(toCapital ? null : value);
		setActiveQuarter(toCapital ? null : value);
	}
</script>

{#if visible}
	<div
		class="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-2 py-1"
		title={$_('quarters.switch_tab', { default: 'Quarter (this tab)' })}
	>
		<IconBuildingCommunity size={18} class="text-gray-500" />
		<select
			value={selected}
			onchange={onChange}
			aria-label={$_('quarters.switch_tab', { default: 'Quarter (this tab)' })}
			class="max-w-[12rem] cursor-pointer truncate border-0 bg-transparent p-0 pr-5 text-sm font-medium text-gray-700 focus:outline-none focus:ring-0"
		>
			{#each quarters as quarter (quarter.canister_id)}
				<option value={quarter.canister_id}>
					{quarter.is_capital ? '★ ' : ''}#{quarter.index ?? 0} {quarter.name} ({quarter.population})
				</option>
			{/each}
		</select>
	</div>
{/if}
