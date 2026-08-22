<!-- Read-only quarter badge (top bar).
     Shows every member which quarter of the federation this browser tab is
     currently connected to. Admins get the interactive QuarterSwitcher instead,
     so this badge is only rendered for non-admins (and only when the realm is an
     actual federation with more than just the capital). The active quarter comes
     from activeQuarterId; its display name/index is resolved from the capital's
     quarter directory already held in realmInfo. -->
<script lang="ts">
	import { IconBuildingCommunity } from '@tabler/icons-svelte';
	import { _ } from 'svelte-i18n';
	import { userProfiles } from '$lib/stores/profiles';
	import { realmInfo } from '$lib/stores/realmInfo';
	import { activeQuarterId } from '$lib/stores/quarters';
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
	// Resolve the active quarter (or fall back to the capital when no quarter is
	// pinned for this tab).
	const active = $derived(
		($activeQuarterId
			? quarters.find((q) => q.canister_id === ($activeQuarterId as string))
			: capital) ?? null
	);
	// Read-only badge for members of an actual federation. Admins use the switcher.
	const visible = $derived(!isAdmin && quarters.length > 1 && !!active);
	const label = $derived(active ? formatQuarterShortLabel(active) : '');
</script>

{#if visible && variant === 'menu'}
	<div class="border-t border-gray-200 px-4 py-2 dark:border-gray-700">
		<p class="mb-0.5 flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
			<IconBuildingCommunity size={14} />
			{$_('quarters.connected_to', { default: 'Connected to this quarter' })}
		</p>
		<p class="text-sm font-medium text-gray-800 dark:text-gray-200">{active ? formatQuarterLabel(active) : label}</p>
	</div>
{:else if visible}
	<div
		class="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-2 py-1"
		title={active ? formatQuarterLabel(active) : $_('quarters.connected_to', { default: 'Connected to this quarter' })}
	>
		<IconBuildingCommunity size={18} class="hidden text-gray-500 sm:block" />
		<span class="max-w-[3.5rem] truncate text-sm font-medium text-gray-700 sm:max-w-[12rem]">{label}</span>
	</div>
{/if}
