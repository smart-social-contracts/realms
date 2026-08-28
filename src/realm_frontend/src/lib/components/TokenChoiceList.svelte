<script lang="ts">
	import {
		CUSTOM_TOKEN_ID,
		SHARED_TOKEN_CATALOG
	} from '$lib/setup/sharedTokens';
	import {
		isTokenChoiceSelectable,
		monetaryUnavailableLabel
	} from '$lib/config/hostTestFlags';

	interface Props {
		selectedId: string;
		monetaryDisabled?: boolean;
		locale?: string;
		name?: string;
		onSelect: (id: string) => void;
	}

	let {
		selectedId,
		monetaryDisabled = false,
		locale = 'en',
		name = 'token',
		onSelect
	}: Props = $props();

	const unavailable = $derived(monetaryUnavailableLabel(locale));
	const customSelectable = $derived(
		isTokenChoiceSelectable(CUSTOM_TOKEN_ID, monetaryDisabled)
	);

	function choose(id: string) {
		if (!isTokenChoiceSelectable(id, monetaryDisabled)) return;
		onSelect(id);
	}
</script>

<div class="setup-wizard__codex-list">
	{#each SHARED_TOKEN_CATALOG as token (token.id)}
		{@const selectable = isTokenChoiceSelectable(token.id, monetaryDisabled)}
		<label
			class="setup-wizard__codex-card setup-wizard__codex-card--compact"
			class:setup-wizard__codex-card--selected={selectedId === token.id}
			class:setup-wizard__codex-card--disabled={!selectable}
		>
			<input
				type="radio"
				{name}
				value={token.id}
				checked={selectedId === token.id}
				disabled={!selectable}
				onchange={() => choose(token.id)}
			/>
			<div class="setup-wizard__codex-card-body">
				<strong>{token.name}</strong>
				<p class="setup-wizard__codex-description text-sm text-gray-600">
					{token.description}
				</p>
				{#if !selectable}
					<p class="text-xs text-gray-500 mt-1">{unavailable}</p>
				{/if}
			</div>
		</label>
	{/each}
	<label
		class="setup-wizard__codex-card setup-wizard__codex-card--compact"
		class:setup-wizard__codex-card--selected={selectedId === CUSTOM_TOKEN_ID}
		class:setup-wizard__codex-card--disabled={!customSelectable}
	>
		<input
			type="radio"
			{name}
			value={CUSTOM_TOKEN_ID}
			checked={selectedId === CUSTOM_TOKEN_ID}
			disabled={!customSelectable}
			onchange={() => choose(CUSTOM_TOKEN_ID)}
		/>
		<div class="setup-wizard__codex-card-body">
			<strong>Custom token</strong>
			<p class="setup-wizard__codex-description text-sm text-gray-600">
				Your own ICRC-1 ledger canister.
			</p>
			{#if !customSelectable}
				<p class="text-xs text-gray-500 mt-1">{unavailable}</p>
			{/if}
		</div>
	</label>
</div>

<style>
	.setup-wizard__codex-list {
		display: grid;
		gap: 0.75rem;
	}

	.setup-wizard__codex-card {
		display: flex;
		flex-direction: row;
		gap: 0.85rem;
		align-items: flex-start;
		border: 1px solid #e2e8f0;
		border-radius: 0.75rem;
		padding: 0.85rem 1rem;
		cursor: pointer;
		background: #ffffff;
	}

	.setup-wizard__codex-card--selected {
		border-color: #0b1120;
		background: #f8fafc;
	}

	.setup-wizard__codex-card--disabled {
		opacity: 0.65;
		cursor: not-allowed;
		background: #f3f4f6;
	}

	.setup-wizard__codex-card input {
		margin-top: 0.2rem;
	}

	.setup-wizard__codex-description {
		margin: 0.25rem 0 0;
	}
</style>
