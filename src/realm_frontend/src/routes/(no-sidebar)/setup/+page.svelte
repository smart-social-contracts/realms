<script lang="ts">
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { Button, Heading, Input, Label, P, Select } from 'flowbite-svelte';
	import {
		completeSetup,
		configureSetupToken,
		fetchSetupState,
		installSetupCodex,
		listAvailableCodices,
		setSetupBranding
	} from '$lib/setup/api';
	import type { AvailableCodex, SetupState } from '$lib/setup/types';
	import { fileToCompressedDataUrl } from '$lib/utils/imageDataUrl';
	import { setupStateStore } from '$lib/stores/setupState';
	import { realmName } from '$lib/stores/realmInfo';

	type WizardStep = 'codex' | 'token' | 'branding' | 'review';

	const steps: { id: WizardStep; label: string; skippable: boolean }[] = [
		{ id: 'codex', label: 'Codex', skippable: false },
		{ id: 'token', label: 'Token', skippable: true },
		{ id: 'branding', label: 'Branding', skippable: true },
		{ id: 'review', label: 'Launch', skippable: false }
	];

	let currentStep = $state<WizardStep>('codex');
	let loading = $state(true);
	let busy = $state(false);
	let error = $state('');
	let setupState = $state<SetupState | null>(null);
	let codices = $state<AvailableCodex[]>([]);
	let selectedCodexId = $state('');
	let selectedVersion = $state('');
	let resolvedCodexVersion = $state('');
	let codexInstallProgress = $state('');
	let tokenSymbol = $state('REALMS');
	let primaryColor = $state('#3b82f6');
	let logoPreview = $state('');
	let backgroundPreview = $state('');
	let logoDataUrl = $state('');
	let backgroundDataUrl = $state('');

	const selectedCodex = $derived(codices.find((c) => c.id === selectedCodexId) ?? null);
	const stepIndex = $derived(steps.findIndex((s) => s.id === currentStep));

	function latestVersion(codex: AvailableCodex): string {
		return codex.versions[codex.versions.length - 1] ?? '';
	}

	function applySetupState(state: SetupState) {
		setupState = state;
		if (state.codex) {
			selectedCodexId = state.codex.package;
			selectedVersion = state.codex.version;
			resolvedCodexVersion = state.codex.version;
		}
		if (state.token && typeof state.token.existing === 'string') {
			tokenSymbol = state.token.existing;
		}
		const colors = state.branding?.colors as { primary?: string } | undefined;
		if (colors?.primary) primaryColor = colors.primary;
		if (typeof state.branding?.logo_data_url === 'string') {
			logoPreview = state.branding.logo_data_url;
			logoDataUrl = state.branding.logo_data_url;
		}
		if (typeof state.branding?.background_data_url === 'string') {
			backgroundPreview = state.branding.background_data_url;
			backgroundDataUrl = state.branding.background_data_url;
		}
	}

	async function loadWizard() {
		loading = true;
		error = '';
		try {
			const [state, available] = await Promise.all([fetchSetupState(), listAvailableCodices()]);
			if (state.status !== 'setup') {
				window.location.replace('/');
				return;
			}
			if (!state.is_caller_authorized) {
				window.location.replace('/');
				return;
			}
			codices = available;
			applySetupState(state);
			if (!selectedCodexId && codices.length > 0) {
				selectedCodexId = codices[0].id;
				selectedVersion = latestVersion(codices[0]);
			} else {
				const codex = codices.find((c) => c.id === selectedCodexId);
				if (codex && !codex.versions.includes(selectedVersion)) {
					selectedVersion = latestVersion(codex);
				}
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load setup wizard';
		} finally {
			loading = false;
		}
	}

	async function handleCodexInstall() {
		if (!selectedCodexId || !selectedVersion) {
			error = 'Choose a codex and version';
			return;
		}
		if (
			setupState?.codex?.package === selectedCodexId &&
			setupState?.codex?.version === selectedVersion
		) {
			currentStep = 'token';
			return;
		}
		busy = true;
		error = '';
		codexInstallProgress = `Installing ${selectedCodexId}@${selectedVersion}… this can take several minutes`;
		try {
			const result = await installSetupCodex({
				package: selectedCodexId,
				version: selectedVersion
			});
			if (!result.success) {
				error = result.error || 'Codex installation failed';
				return;
			}
			resolvedCodexVersion = result.resolved_version || selectedVersion;
			const refreshed = await fetchSetupState();
			applySetupState(refreshed);
			currentStep = 'token';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Codex installation failed';
		} finally {
			busy = false;
			codexInstallProgress = '';
		}
	}

	async function handleTokenSave() {
		busy = true;
		error = '';
		try {
			const result = await configureSetupToken({ existing: tokenSymbol.trim() || 'REALMS' });
			if (!result.success) {
				error = result.error || 'Token configuration failed';
				return;
			}
			const refreshed = await fetchSetupState();
			applySetupState(refreshed);
			currentStep = 'branding';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Token configuration failed';
		} finally {
			busy = false;
		}
	}

	async function handleBrandingSave() {
		busy = true;
		error = '';
		try {
			const payload: {
				logo_data_url?: string;
				background_data_url?: string;
				colors?: { primary?: string };
			} = {};
			if (logoDataUrl) payload.logo_data_url = logoDataUrl;
			if (backgroundDataUrl) payload.background_data_url = backgroundDataUrl;
			if (primaryColor.trim()) payload.colors = { primary: primaryColor.trim() };

			const result = await setSetupBranding(payload);
			if (!result.success) {
				error = result.error || 'Branding update failed';
				return;
			}
			const refreshed = await fetchSetupState();
			applySetupState(refreshed);
			currentStep = 'review';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Branding update failed';
		} finally {
			busy = false;
		}
	}

	async function handleLaunch() {
		busy = true;
		error = '';
		try {
			const result = await completeSetup();
			if (!result.success) {
				error = result.error || 'Could not launch realm';
				return;
			}
			await setupStateStore.refresh();
			window.location.replace('/');
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not launch realm';
		} finally {
			busy = false;
		}
	}

	async function onLogoChange(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;
		try {
			logoDataUrl = await fileToCompressedDataUrl(file);
			logoPreview = logoDataUrl;
			error = '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not process logo';
		}
	}

	async function onBackgroundChange(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;
		try {
			backgroundDataUrl = await fileToCompressedDataUrl(file);
			backgroundPreview = backgroundDataUrl;
			error = '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not process background';
		}
	}

	function goToStep(step: WizardStep) {
		currentStep = step;
		error = '';
	}

	function skipStep() {
		const step = steps[stepIndex];
		if (!step?.skippable) return;
		const next = steps[stepIndex + 1];
		if (next) currentStep = next.id;
	}

	onMount(() => {
		if (!browser) return;
		void loadWizard();
		const timer = setInterval(async () => {
			try {
				const state = await fetchSetupState();
				if (state.status !== 'setup') {
					window.location.replace('/');
				}
			} catch {
				// ignore transient poll errors
			}
		}, 8000);
		return () => clearInterval(timer);
	});
</script>

<svelte:head>
	<title>Setup {$realmName || 'Realm'}</title>
</svelte:head>

<div class="setup-wizard">
	<div class="setup-wizard__shell">
		<header class="setup-wizard__header">
			<img src="/images/logo_sphere_only.svg" alt="" class="setup-wizard__mark" />
			<div>
				<p class="setup-wizard__eyebrow">Realm setup</p>
				<Heading tag="h1" class="setup-wizard__title">Configure {$realmName || 'your realm'}</Heading>
			</div>
		</header>

		<nav class="setup-wizard__steps" aria-label="Setup steps">
			{#each steps as step, index (step.id)}
				<button
					type="button"
					class="setup-wizard__step"
					class:setup-wizard__step--active={step.id === currentStep}
					class:setup-wizard__step--done={index < stepIndex}
					onclick={() => goToStep(step.id)}
				>
					<span class="setup-wizard__step-index">{index + 1}</span>
					{step.label}
				</button>
			{/each}
		</nav>

		{#if loading}
			<P>Loading setup wizard…</P>
		{:else}
			{#if error}
				<div class="setup-wizard__error" role="alert">{error}</div>
			{/if}

			{#if currentStep === 'codex'}
				<section class="setup-wizard__panel">
					<Heading tag="h2" class="text-xl font-semibold">Choose a codex</Heading>
					<P class="text-gray-600">Pick the governance package that defines how this realm runs.</P>

					<div class="setup-wizard__codex-list">
						{#each codices as codex (codex.id)}
							<label class="setup-wizard__codex-card" class:setup-wizard__codex-card--selected={selectedCodexId === codex.id}>
								<input
									type="radio"
									name="codex"
									value={codex.id}
									bind:group={selectedCodexId}
									onchange={() => {
										selectedVersion = latestVersion(codex);
									}}
								/>
								<div>
									<strong>{codex.name || codex.id}</strong>
									{#if codex.description}
										<P class="text-sm text-gray-600">{codex.description}</P>
									{/if}
								</div>
							</label>
						{/each}
					</div>

					{#if selectedCodex}
						<div class="setup-wizard__field">
							<Label for="codex-version">Version</Label>
							<Select id="codex-version" bind:value={selectedVersion} items={selectedCodex.versions.map((v) => ({ value: v, name: v }))} />
						</div>
					{/if}

					{#if resolvedCodexVersion}
						<P class="text-sm text-green-700">Installed codex version: {resolvedCodexVersion}</P>
					{/if}

					<div class="setup-wizard__actions">
						{#if codexInstallProgress}
							<P class="text-sm text-gray-600">{codexInstallProgress}</P>
						{/if}
						<Button color="blue" disabled={busy || !selectedCodexId} onclick={handleCodexInstall}>
							{busy ? 'Installing…' : setupState?.codex ? 'Continue' : 'Install codex'}
						</Button>
					</div>
				</section>
			{:else if currentStep === 'token'}
				<section class="setup-wizard__panel">
					<Heading tag="h2" class="text-xl font-semibold">Token</Heading>
					<P class="text-gray-600">Select an existing token symbol for this realm (v1).</P>
					<div class="setup-wizard__field">
						<Label for="token-symbol">Existing token symbol</Label>
						<Input id="token-symbol" bind:value={tokenSymbol} placeholder="REALMS" />
					</div>
					<div class="setup-wizard__actions">
						<Button color="light" disabled={busy} onclick={skipStep}>Skip</Button>
						<Button color="blue" disabled={busy} onclick={handleTokenSave}>
							{busy ? 'Saving…' : 'Save token'}
						</Button>
					</div>
				</section>
			{:else if currentStep === 'branding'}
				<section class="setup-wizard__panel setup-wizard__panel--branding">
					<div>
						<Heading tag="h2" class="text-xl font-semibold">Branding</Heading>
						<P class="text-gray-600">Optional logo, background, and primary color (max 1.5MB each).</P>

						<div class="setup-wizard__field">
							<Label for="logo-file">Logo</Label>
							<input id="logo-file" type="file" accept="image/*" onchange={onLogoChange} />
						</div>
						<div class="setup-wizard__field">
							<Label for="background-file">Background</Label>
							<input id="background-file" type="file" accept="image/*" onchange={onBackgroundChange} />
						</div>
						<div class="setup-wizard__field">
							<Label for="primary-color">Primary color</Label>
							<Input id="primary-color" type="color" bind:value={primaryColor} class="h-11 w-24 p-1" />
						</div>

						<div class="setup-wizard__actions">
							<Button color="light" disabled={busy} onclick={skipStep}>Skip</Button>
							<Button color="blue" disabled={busy} onclick={handleBrandingSave}>
								{busy ? 'Saving…' : 'Save branding'}
							</Button>
						</div>
					</div>

					<div
						class="setup-wizard__preview"
						style={`--preview-primary:${primaryColor}; background-image:${backgroundPreview ? `url(${backgroundPreview})` : 'none'};`}
					>
						<div class="setup-wizard__preview-card">
							{#if logoPreview}
								<img src={logoPreview} alt="Logo preview" class="setup-wizard__preview-logo" />
							{/if}
							<p class="setup-wizard__preview-title">{$realmName || 'Your realm'}</p>
							<span class="setup-wizard__preview-chip">Preview</span>
						</div>
					</div>
				</section>
			{:else}
				<section class="setup-wizard__panel">
					<Heading tag="h2" class="text-xl font-semibold">Review & launch</Heading>
					<P class="text-gray-600">Confirm your choices, then launch the realm into alpha.</P>

					<dl class="setup-wizard__summary">
						<div>
							<dt>Codex</dt>
							<dd>{setupState?.codex?.package || selectedCodexId || 'Not installed'}</dd>
						</div>
						<div>
							<dt>Codex version</dt>
							<dd>{setupState?.codex?.version || resolvedCodexVersion || '—'}</dd>
						</div>
						<div>
							<dt>Token</dt>
							<dd>{setupState?.token?.existing || tokenSymbol || 'Skipped'}</dd>
						</div>
						<div>
							<dt>Branding</dt>
							<dd>
								{#if setupState?.branding || logoDataUrl || backgroundDataUrl}
									Logo {logoPreview ? '✓' : '—'}, background {backgroundPreview ? '✓' : '—'},
									color {primaryColor}
								{:else}
									Skipped
								{/if}
							</dd>
						</div>
					</dl>

					<div class="setup-wizard__actions">
						<Button color="light" disabled={busy} onclick={() => goToStep('codex')}>Back</Button>
						<Button color="blue" disabled={busy || !setupState?.codex} onclick={handleLaunch}>
							{busy ? 'Launching…' : 'Launch realm'}
						</Button>
					</div>
				</section>
			{/if}
		{/if}
	</div>
</div>

<style>
	.setup-wizard {
		min-height: 100vh;
		min-height: 100dvh;
		background: #f8fafc;
		padding: 1.5rem;
	}

	.setup-wizard__shell {
		max-width: 960px;
		margin: 0 auto;
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 1rem;
		padding: 1.5rem;
		box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
	}

	.setup-wizard__header {
		display: flex;
		gap: 1rem;
		align-items: center;
		margin-bottom: 1.5rem;
	}

	.setup-wizard__mark {
		width: 2.75rem;
		height: 2.75rem;
	}

	.setup-wizard__eyebrow {
		font-size: 0.875rem;
		color: #64748b;
		margin-bottom: 0.25rem;
	}

	:global(.setup-wizard__title) {
		font-size: 1.5rem;
		font-weight: 600;
	}

	.setup-wizard__steps {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		margin-bottom: 1.5rem;
	}

	.setup-wizard__step {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		border: 1px solid #e2e8f0;
		background: #f8fafc;
		color: #334155;
		border-radius: 999px;
		padding: 0.35rem 0.85rem;
		font-size: 0.875rem;
	}

	.setup-wizard__step--active {
		border-color: #3b82f6;
		background: #eff6ff;
		color: #1d4ed8;
	}

	.setup-wizard__step--done {
		border-color: #86efac;
		background: #f0fdf4;
		color: #166534;
	}

	.setup-wizard__step-index {
		display: inline-flex;
		width: 1.25rem;
		height: 1.25rem;
		align-items: center;
		justify-content: center;
		border-radius: 999px;
		background: rgba(15, 23, 42, 0.08);
		font-size: 0.75rem;
	}

	.setup-wizard__panel {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.setup-wizard__panel--branding {
		display: grid;
		grid-template-columns: 1fr;
		gap: 1.5rem;
	}

	@media (min-width: 900px) {
		.setup-wizard__panel--branding {
			grid-template-columns: 1.1fr 0.9fr;
		}
	}

	.setup-wizard__codex-list {
		display: grid;
		gap: 0.75rem;
	}

	.setup-wizard__codex-card {
		display: flex;
		gap: 0.75rem;
		align-items: flex-start;
		border: 1px solid #e2e8f0;
		border-radius: 0.75rem;
		padding: 0.85rem 1rem;
		cursor: pointer;
	}

	.setup-wizard__codex-card--selected {
		border-color: #3b82f6;
		background: #eff6ff;
	}

	.setup-wizard__field {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}

	.setup-wizard__actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		margin-top: 0.5rem;
	}

	.setup-wizard__error {
		background: #fef2f2;
		border: 1px solid #fecaca;
		color: #b91c1c;
		border-radius: 0.5rem;
		padding: 0.75rem 1rem;
		margin-bottom: 1rem;
	}

	.setup-wizard__summary {
		display: grid;
		gap: 0.75rem;
	}

	.setup-wizard__summary dt {
		font-size: 0.75rem;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: #64748b;
	}

	.setup-wizard__summary dd {
		font-size: 1rem;
		color: #0f172a;
	}

	.setup-wizard__preview {
		min-height: 220px;
		border-radius: 0.75rem;
		border: 1px solid #e2e8f0;
		background-color: #0f172a;
		background-size: cover;
		background-position: center;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 1rem;
	}

	.setup-wizard__preview-card {
		background: rgba(255, 255, 255, 0.92);
		border-radius: 0.75rem;
		padding: 1rem 1.25rem;
		text-align: center;
		min-width: 12rem;
	}

	.setup-wizard__preview-logo {
		max-height: 3rem;
		margin: 0 auto 0.5rem;
	}

	.setup-wizard__preview-title {
		font-weight: 600;
		color: #0f172a;
	}

	.setup-wizard__preview-chip {
		display: inline-block;
		margin-top: 0.5rem;
		padding: 0.15rem 0.5rem;
		border-radius: 999px;
		background: var(--preview-primary, #3b82f6);
		color: white;
		font-size: 0.75rem;
	}
</style>
