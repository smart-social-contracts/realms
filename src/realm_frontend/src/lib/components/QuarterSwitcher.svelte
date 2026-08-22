<!-- Admin-only quarter switcher (top bar).
     Lets an admin point this browser tab at a specific quarter (or the capital).
     It drives setActiveQuarter(), so every quarterBackend / ctx.backend call —
     including the realm_settings Quarters panel reads — targets the selection.
     Only shown to admins when the realm actually has more than one quarter.
     Quarter list comes from the realmInfo store (capital.status().quarters),
     fetched from the capital backend on navbar mount. -->
<script lang="ts">
	import { IconBuildingCommunity } from '@tabler/icons-svelte';
	import { _ } from 'svelte-i18n';
	import { userProfiles } from '$lib/stores/profiles';
	import { realmInfo } from '$lib/stores/realmInfo';
	import { activeQuarterId } from '$lib/stores/quarters';
	// @ts-ignore - canisters.js is untyped
	import { setActiveQuarter } from '$lib/canisters';
	import { formatQuarterLabel, formatQuarterShortLabel } from '$lib/utils/quarterLabels';

	let { variant = 'chip' }: { variant?: 'chip' | 'menu' } = $props();

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

{#if visible && variant === 'menu'}
	<div class="border-t border-gray-200 px-4 py-2 dark:border-gray-700">
		<label class="mb-1 flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400" for="quarter-switch-menu">
			<IconBuildingCommunity size={14} />
			{$_('quarters.switch_tab', { default: 'Quarter (this tab)' })}
		</label>
		<select
			id="quarter-switch-menu"
			value={selected}
			onchange={onChange}
			class="w-full rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-sm font-medium text-gray-700 outline-none focus:border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
		>
			{#each quarters as quarter (quarter.canister_id)}
				<option value={quarter.canister_id}>
					{formatQuarterLabel(quarter)}
				</option>
			{/each}
		</select>
	</div>
{:else if visible}
	<div
		class="inline-flex max-w-[5.5rem] items-center gap-1 rounded-lg border border-gray-200 bg-white px-1.5 py-1 sm:max-w-none sm:gap-1.5 sm:px-2"
		title={`${formatQuarterLabel(quarters.find((q) => q.canister_id === selected) ?? null)} · ${$_('quarters.switch_tab', { default: 'Quarter (this tab)' })}`}
	>
		<IconBuildingCommunity size={18} class="hidden text-gray-500 sm:block" />
		<select
			value={selected}
			onchange={onChange}
			aria-label={$_('quarters.switch_tab', { default: 'Quarter (this tab)' })}
			class="max-w-[3.25rem] cursor-pointer truncate border-0 bg-transparent p-0 pr-4 text-sm font-medium text-gray-700 focus:outline-none focus:ring-0 sm:max-w-[12rem] sm:pr-5"
		>
			{#each quarters as quarter (quarter.canister_id)}
				<option value={quarter.canister_id} title={formatQuarterLabel(quarter)}>
					{formatQuarterShortLabel(quarter)}
				</option>
			{/each}
		</select>
	</div>
{/if}
