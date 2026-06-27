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
	const label = $derived(
		active
			? active.is_capital
				? `★ ${active.name || 'Capital'}`
				: `#${active.index ?? 0} ${active.name || 'Quarter'}`
			: ''
	);
</script>

{#if visible}
	<div
		class="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-2 py-1"
		title={$_('quarters.connected_to', { default: 'Connected to this quarter' })}
	>
		<IconBuildingCommunity size={18} class="text-gray-500" />
		<span class="max-w-[12rem] truncate text-sm font-medium text-gray-700">{label}</span>
	</div>
{/if}
