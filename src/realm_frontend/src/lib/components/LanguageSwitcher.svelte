<script lang="ts">
	/**
	 * Personal locale picker for user settings.
	 * Do not mount this in host chrome (issue #361).
	 */
	import { localeLabel } from '$lib/i18n/realmLocales';

	interface Props {
		locales?: string[];
		value?: string;
		allowEmpty?: boolean;
		emptyLabel?: string;
		disabled?: boolean;
		onchange?: (value: string) => void;
	}

	let {
		locales = [],
		value = '',
		allowEmpty = true,
		emptyLabel = '',
		disabled = false,
		onchange
	}: Props = $props();
</script>

<div class="language-switcher">
	<select
		value={value}
		{disabled}
		onchange={(e) => onchange?.(e.currentTarget.value)}
		class="bg-transparent border border-gray-300 rounded px-2 py-1 text-sm dark:border-gray-600 dark:text-white"
	>
		{#if allowEmpty}
			<option value="">{emptyLabel}</option>
		{/if}
		{#each locales as loc (loc)}
			<option value={loc}>{localeLabel(loc)}</option>
		{/each}
	</select>
</div>

<style>
	.language-switcher {
		display: inline-block;
	}
</style>
