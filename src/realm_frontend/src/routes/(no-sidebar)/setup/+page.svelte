<script lang="ts">
	import { onMount } from 'svelte';
	import { goto, replaceState } from '$app/navigation';
	import { browser } from '$app/environment';
	import { page } from '$app/state';
	import { Button, Heading, Input, Label, P } from 'flowbite-svelte';
	import {
		LAUNCH_STATUS_POLL_MS,
		fetchSetupDraftAsset,
		fetchSetupLaunchStatus,
		fetchSetupState,
		listAvailableCodices,
		saveSetupDraft,
		startSetupLaunch
	} from '$lib/setup/api';
	import { fetchCodexDescription, repositoryUrl } from '$lib/setup/codexDocs';
	import type { AvailableCodex, SetupLaunchState, SetupState } from '$lib/setup/types';
	import {
		LAUNCH_PHASES,
		canAdvanceFromCodexStep,
		canNavigateToWizardStep,
		getCodexStepPrimaryLabel,
		getPreviousWizardStep,
		getWelcomeAdvanceStep,
		isCodexPrimaryActionDisabled,
		isSetupCatalogCodex,
		reconcileCodexVersion,
		resolveInitialWizardStep,
		resolveSelectedCodexVersion,
		shouldClearCodexAdvanceError,
		stepToUrlToken,
		type WizardStep
	} from '$lib/setup/wizardLogic';
	import { isEmbeddedInPortal, portalNavPush } from '$lib/portal-bridge';
	import { generateBrandingAssets } from '$lib/setup/brandingGenerate';
	import { fileToCompressedDataUrl } from '$lib/utils/imageDataUrl';
	import { setupStateStore } from '$lib/stores/setupState';
	import { realmManifesto, realmName, realmWelcomeMessage } from '$lib/stores/realmInfo';
	import PublicDashboardPreview from '$lib/setup/PublicDashboardPreview.svelte';
	import BrandingDropzone from '$lib/setup/BrandingDropzone.svelte';
	import { get } from 'svelte/store';

	const WELCOME_FOUNDING_LINE =
		'You are founding a realm — a digital polity whose rules and processes are verifiable and tamper-proof. Choose how it governs, what it values, and how it looks — then bring it to life.';

	const WELCOME_MESSAGE_MAX = 1024;
	const MANIFESTO_MAX = 256;
	const IDENTITY_DRAFT_DEBOUNCE_MS = 500;

	const steps: { id: WizardStep; label: string; skippable: boolean }[] = [
		{ id: 'welcome', label: 'Welcome', skippable: false },
		{ id: 'codex', label: 'Codex', skippable: false },
		{ id: 'token', label: 'Token', skippable: true },
		{ id: 'branding', label: 'Branding', skippable: true },
		{ id: 'review', label: 'Launch', skippable: false }
	];

	const primaryButtonClass =
		'bg-gray-900 text-white hover:bg-gray-700 dark:bg-gray-100 dark:text-gray-900';
	const secondaryButtonClass =
		'border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700';

	let currentStep = $state<WizardStep>('welcome');
	let loading = $state(true);
	let busy = $state(false);
	let error = $state('');
	let setupState = $state<SetupState | null>(null);
	let launchState = $state<SetupLaunchState | null>(null);
	let codices = $state<AvailableCodex[]>([]);
	let selectedCodexId = $state('');
	let selectedVersion = $state('');
	let resolvedCodexVersion = $state('');
	let tokenSymbol = $state('REALMS');
	let tokenCanisterId = $state('');
	let primaryColor = $state('#3b82f6');
	let logoPreview = $state('');
	let backgroundPreview = $state('');
	let logoDataUrl = $state('');
	let backgroundDataUrl = $state('');
	let welcomeMessage = $state('');
	let manifesto = $state('');
	let welcomeMessageTouched = $state(false);
	let manifestoTouched = $state(false);
	let leftSetup = $state(false);
	let urlSynced = $state(false);
	let codexDescriptions = $state<Record<string, string>>({});
	let codexDescriptionExpanded = $state<Record<string, boolean>>({});
	let draftAssetsLoading = $state(false);
	let identityDraftTimer: ReturnType<typeof setTimeout> | null = null;
	let launchPollTimer: ReturnType<typeof setInterval> | null = null;
	let generatingBranding = $state(false);
	let brandingSource = $state<'generate' | 'upload'>('generate');

	const stepIndex = $derived(steps.findIndex((s) => s.id === currentStep));
	const isWelcomeStep = $derived(currentStep === 'welcome');
	const previousStep = $derived(getPreviousWizardStep(currentStep));
	const codexPrimaryLabel = $derived(getCodexStepPrimaryLabel(setupState, busy));
	const codexPrimaryDisabled = $derived(
		isCodexPrimaryActionDisabled(busy, selectedCodexId, selectedVersion, setupState)
	);
	const welcomeMessageOverLimit = $derived(welcomeMessage.length > WELCOME_MESSAGE_MAX);
	const manifestoOverLimit = $derived(manifesto.length > MANIFESTO_MAX);
	const brandingTextInvalid = $derived(welcomeMessageOverLimit || manifestoOverLimit);
	const launchRunning = $derived(launchState?.status === 'running');
	const launchFailed = $derived(launchState?.status === 'failed');
	const launchCompleted = $derived(launchState?.status === 'completed');
	const launchIdle = $derived(!launchState || launchState.status === 'idle');
	const summaryCodexPackage = $derived(
		setupState?.draft?.codex?.package || setupState?.codex?.package || selectedCodexId || ''
	);
	const summaryCodexVersion = $derived(
		setupState?.draft?.codex?.version ||
			setupState?.codex?.version ||
			resolvedCodexVersion ||
			selectedVersion ||
			''
	);
	const summaryTokenSymbol = $derived(
		(setupState?.draft?.token?.symbol as string | undefined) ||
			(setupState?.token?.symbol as string | undefined) ||
			(setupState?.token?.existing as string | undefined) ||
			tokenSymbol ||
			''
	);
	const hasBrandingDraft = $derived(
		Boolean(
			setupState?.draft?.branding?.logo ||
				setupState?.draft?.branding?.background ||
				setupState?.draft?.branding?.colors?.primary ||
				logoDataUrl ||
				backgroundDataUrl ||
				welcomeMessage.trim() ||
				manifesto.trim()
		)
	);

	$effect(() => {
		if (shouldClearCodexAdvanceError(currentStep, error)) {
			error = '';
		}
	});

	$effect(() => {
		if (currentStep === 'branding' || currentStep === 'review') {
			void ensureDraftAssetsLoaded();
		}
	});

	function syncStepToUrl() {
		if (!browser || !urlSynced) return;
		const token = stepToUrlToken(currentStep);
		const url = new URL(page.url);
		if (url.searchParams.get('step') !== token) {
			url.searchParams.set('step', token);
			replaceState(url, page.state);
		}
		// replaceState does not fire afterNavigate, so the portal bar would
		// stay at /setup unless we push the query ourselves.
		if (isEmbeddedInPortal()) {
			const params = new URLSearchParams(url.search);
			params.delete('portal');
			params.delete('slug');
			const qs = params.toString();
			portalNavPush(`${url.pathname}${qs ? `?${qs}` : ''}`, { replace: true });
		}
	}

	function navigateToStep(step: WizardStep) {
		currentStep = step;
		error = '';
		syncStepToUrl();
	}

	function applyInitialStepFromState(state: SetupState) {
		const step = resolveInitialWizardStep(state, page.url.searchParams.get('step'));
		currentStep = step;
	}

	function latestVersion(codex: AvailableCodex): string {
		return codex.versions[codex.versions.length - 1] ?? '';
	}

	function codexRepositoryHref(codex: AvailableCodex): string {
		return codex.repository?.trim() || repositoryUrl(codex.id);
	}

	function resolveWelcomeFromState(state: SetupState): string {
		if (typeof state.draft?.identity?.welcome_message === 'string') {
			return state.draft.identity.welcome_message;
		}
		const branding = state.branding as Record<string, unknown> | null;
		if (typeof state.identity?.welcome_message === 'string') {
			return state.identity.welcome_message;
		}
		if (typeof branding?.welcome_message === 'string') {
			return branding.welcome_message;
		}
		if (typeof state.realm_welcome_message === 'string') {
			return state.realm_welcome_message;
		}
		return get(realmWelcomeMessage);
	}

	function resolveManifestoFromState(state: SetupState): string {
		if (typeof state.draft?.identity?.manifesto === 'string') {
			return state.draft.identity.manifesto;
		}
		const branding = state.branding as Record<string, unknown> | null;
		if (typeof state.identity?.manifesto === 'string') {
			return state.identity.manifesto;
		}
		if (typeof branding?.manifesto === 'string') {
			return branding.manifesto;
		}
		if (typeof state.realm_manifesto === 'string') {
			return state.realm_manifesto;
		}
		return get(realmManifesto);
	}

	function applySetupState(state: SetupState) {
		setupState = state;
		if (state.launch) {
			launchState = state.launch;
		}

		const codex = state.draft?.codex ?? state.codex;
		if (codex?.package && codex?.version) {
			selectedCodexId = codex.package;
			selectedVersion = codex.version;
			resolvedCodexVersion = codex.version;
		}

		const token = state.draft?.token ?? state.token;
		if (token) {
			if (typeof token.symbol === 'string') {
				tokenSymbol = token.symbol;
			}
			if (typeof token.token_canister_id === 'string') {
				tokenCanisterId = token.token_canister_id;
			}
			if (typeof token.existing === 'string') {
				tokenSymbol = token.existing;
			}
		}

		const branding = state.draft?.branding ?? state.branding;
		if (branding) {
			const colors = branding.colors as { primary?: string } | undefined;
			if (colors?.primary) primaryColor = colors.primary;
			if (typeof branding.logo_data_url === 'string') {
				logoPreview = branding.logo_data_url;
				logoDataUrl = branding.logo_data_url;
			}
			if (typeof branding.background_data_url === 'string') {
				backgroundPreview = branding.background_data_url;
				backgroundDataUrl = branding.background_data_url;
			}
		}

		if (!welcomeMessageTouched) {
			welcomeMessage = resolveWelcomeFromState(state);
		}
		if (!manifestoTouched) {
			manifesto = resolveManifestoFromState(state);
		}
	}

	async function loadCodexDescriptions(available: AvailableCodex[]) {
		const entries = await Promise.all(
			available.map(async (codex) => {
				const description = await fetchCodexDescription(codex.id, codex.description ?? '');
				return [codex.id, description] as const;
			})
		);
		codexDescriptions = Object.fromEntries(entries);
	}

	async function ensureDraftAssetsLoaded() {
		const branding = setupState?.draft?.branding;
		if (!branding || draftAssetsLoading) return;
		const needsLogo = Boolean(branding.logo) && !logoDataUrl;
		const needsBackground = Boolean(branding.background) && !backgroundDataUrl;
		if (!needsLogo && !needsBackground) return;

		draftAssetsLoading = true;
		try {
			if (needsLogo) {
				const url = await fetchSetupDraftAsset('logo');
				if (url) {
					logoDataUrl = url;
					logoPreview = url;
				}
			}
			if (needsBackground) {
				const url = await fetchSetupDraftAsset('background');
				if (url) {
					backgroundDataUrl = url;
					backgroundPreview = url;
				}
			}
		} catch {
			// ignore transient asset fetch errors
		} finally {
			draftAssetsLoading = false;
		}
	}

	async function persistDraft(
		partial: Parameters<typeof saveSetupDraft>[0],
		options?: { refresh?: boolean }
	): Promise<boolean> {
		const result = await saveSetupDraft(partial);
		if (!result.success) {
			error = result.error || 'Could not save setup draft';
			return false;
		}
		if (result.draft && setupState) {
			setupState = { ...setupState, draft: result.draft };
		}
		if (options?.refresh !== false) {
			const refreshed = await fetchSetupState();
			applySetupState(refreshed);
		}
		return true;
	}

	function scheduleIdentityDraftSave() {
		if (identityDraftTimer) clearTimeout(identityDraftTimer);
		identityDraftTimer = setTimeout(() => {
			void persistDraft(
				{
					identity: {
						welcome_message: welcomeMessage.trim(),
						manifesto: manifesto.trim()
					}
				},
				{ refresh: false }
			);
		}, IDENTITY_DRAFT_DEBOUNCE_MS);
	}

	function stopLaunchPolling() {
		if (launchPollTimer) {
			clearInterval(launchPollTimer);
			launchPollTimer = null;
		}
	}

	async function pollLaunchStatus() {
		try {
			const launch = await fetchSetupLaunchStatus();
			launchState = launch;
			if (launch.status === 'completed') {
				stopLaunchPolling();
				await setupStateStore.refresh();
				leftSetup = true;
				void goto('/', { replaceState: true });
			} else if (launch.status === 'failed') {
				stopLaunchPolling();
			}
		} catch {
			// ignore transient poll errors
		}
	}

	function startLaunchPolling() {
		stopLaunchPolling();
		launchPollTimer = setInterval(() => {
			void pollLaunchStatus();
		}, LAUNCH_STATUS_POLL_MS);
	}

	async function loadWizard() {
		loading = true;
		error = '';
		try {
			const [state, available] = await Promise.all([fetchSetupState(), listAvailableCodices()]);
			if (state.status !== 'setup') {
				leftSetup = true;
				void goto('/', { replaceState: true });
				return;
			}
			if (!state.is_caller_authorized) {
				await setupStateStore.refresh();
				return;
			}
			codices = available.filter((codex) => isSetupCatalogCodex(codex.id));
			applySetupState(state);
			void loadCodexDescriptions(available);
			if (!selectedCodexId && codices.length > 0) {
				selectedCodexId = codices[0].id;
				selectedVersion = latestVersion(codices[0]);
			} else {
				const codex = codices.find((c) => c.id === selectedCodexId);
				if (codex) {
					const savedVersion =
						state.draft?.codex?.version || state.codex?.version || selectedVersion;
					selectedVersion = reconcileCodexVersion(
						codex.versions,
						selectedVersion,
						savedVersion,
						latestVersion
					);
				}
			}
			applyInitialStepFromState(state);
			if (state.launch?.status === 'running') {
				startLaunchPolling();
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load setup wizard';
		} finally {
			urlSynced = true;
			syncStepToUrl();
			loading = false;
		}
	}

	async function handleWelcomeContinue() {
		busy = true;
		error = '';
		try {
			const ok = await persistDraft({ step: 'codex' });
			if (!ok) return;
			navigateToStep(getWelcomeAdvanceStep());
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not save setup draft';
		} finally {
			busy = false;
		}
	}

	async function handleCodexContinue() {
		const versionToSave = resolveSelectedCodexVersion(selectedVersion, setupState);
		if (!selectedCodexId || !versionToSave) {
			error = 'Choose a codex and version';
			return;
		}
		selectedVersion = versionToSave;

		if (canAdvanceFromCodexStep(setupState) && setupState?.draft?.codex?.package === selectedCodexId &&
			setupState?.draft?.codex?.version === versionToSave &&
			setupState?.draft?.step &&
			['token', 'branding', 'review'].includes(setupState.draft.step)) {
			navigateToStep('token');
			return;
		}

		busy = true;
		error = '';
		try {
			const ok = await persistDraft({
				step: 'token',
				codex: {
					package: selectedCodexId,
					version: versionToSave
				}
			});
			if (!ok) return;
			resolvedCodexVersion = versionToSave;
			navigateToStep('token');
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not save codex draft';
		} finally {
			busy = false;
		}
	}

	async function handleTokenSave() {
		busy = true;
		error = '';
		try {
			const token: Record<string, string> = {
				symbol: tokenSymbol.trim() || 'REALMS'
			};
			const canisterId = tokenCanisterId.trim();
			if (canisterId) {
				token.token_canister_id = canisterId;
			}
			const ok = await persistDraft({ step: 'branding', token });
			if (!ok) return;
			navigateToStep('branding');
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not save token draft';
		} finally {
			busy = false;
		}
	}

	async function handleTokenSkip() {
		busy = true;
		error = '';
		try {
			const ok = await persistDraft({ step: 'branding', token: null });
			if (!ok) return;
			navigateToStep('branding');
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not save token draft';
		} finally {
			busy = false;
		}
	}

	async function handleBrandingSave() {
		if (brandingTextInvalid) {
			error = welcomeMessageOverLimit
				? `Welcome message must be ${WELCOME_MESSAGE_MAX} characters or fewer`
				: `Manifesto must be ${MANIFESTO_MAX} characters or fewer`;
			return;
		}

		busy = true;
		error = '';
		try {
			const branding: {
				logo_data_url?: string;
				background_data_url?: string;
				colors?: { primary?: string };
			} = {};
			if (logoDataUrl) branding.logo_data_url = logoDataUrl;
			if (backgroundDataUrl) branding.background_data_url = backgroundDataUrl;
			if (primaryColor.trim()) branding.colors = { primary: primaryColor.trim() };

			const ok = await persistDraft({
				step: 'review',
				branding,
				identity: {
					welcome_message: welcomeMessage.trim(),
					manifesto: manifesto.trim()
				}
			});
			if (!ok) return;
			navigateToStep('review');
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not save branding draft';
		} finally {
			busy = false;
		}
	}

	async function handleBrandingSkip() {
		busy = true;
		error = '';
		try {
			const ok = await persistDraft({
				step: 'review',
				identity: {
					welcome_message: welcomeMessage.trim(),
					manifesto: manifesto.trim()
				}
			});
			if (!ok) return;
			navigateToStep('review');
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not save branding draft';
		} finally {
			busy = false;
		}
	}

	async function handleLaunch() {
		busy = true;
		error = '';
		try {
			const result = await startSetupLaunch();
			if (!result.success) {
				error = result.error || 'Could not start launch';
				return;
			}
			if (result.launch) {
				launchState = result.launch;
			}
			startLaunchPolling();
			void pollLaunchStatus();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not start launch';
		} finally {
			busy = false;
		}
	}

	function generateBrandingFromIdentity() {
		generatingBranding = true;
		error = '';
		try {
			const assets = generateBrandingAssets({
				realmName: $realmName || 'Realm',
				manifesto
			});
			logoDataUrl = assets.logoDataUrl;
			logoPreview = assets.logoDataUrl;
			backgroundDataUrl = assets.backgroundDataUrl;
			backgroundPreview = assets.backgroundDataUrl;
			primaryColor = assets.primaryColor;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not generate branding';
		} finally {
			generatingBranding = false;
		}
	}

	async function onLogoFile(file: File) {
		try {
			logoDataUrl = await fileToCompressedDataUrl(file);
			logoPreview = logoDataUrl;
			error = '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not process logo';
		}
	}

	async function onBackgroundFile(file: File) {
		try {
			backgroundDataUrl = await fileToCompressedDataUrl(file);
			backgroundPreview = backgroundDataUrl;
			error = '';
		} catch (e) {
			error = e instanceof Error ? e.message : 'Could not process background';
		}
	}

	function goToStep(step: WizardStep) {
		const navigation = canNavigateToWizardStep(currentStep, step, setupState);
		if (!navigation.allowed) {
			if (navigation.showError && navigation.errorMessage) {
				error = navigation.errorMessage;
			}
			return;
		}
		navigateToStep(step);
	}

	function goBack() {
		const previous = getPreviousWizardStep(currentStep);
		if (!previous) return;
		navigateToStep(previous);
	}

	function skipStep() {
		const step = steps[stepIndex];
		if (!step?.skippable) return;
		if (currentStep === 'token') {
			void handleTokenSkip();
			return;
		}
		if (currentStep === 'branding') {
			void handleBrandingSkip();
		}
	}

	function toggleCodexDescription(codexId: string) {
		codexDescriptionExpanded = {
			...codexDescriptionExpanded,
			[codexId]: !codexDescriptionExpanded[codexId]
		};
	}

	function launchStepLabel(name: string): string {
		return LAUNCH_PHASES.find((phase) => phase.name === name)?.label ?? name;
	}

	function launchStepStatus(name: string): string {
		return launchState?.steps.find((step) => step.name === name)?.status ?? 'pending';
	}

	function launchStepError(name: string): string | null {
		return launchState?.steps.find((step) => step.name === name)?.error ?? null;
	}

	onMount(() => {
		if (!browser) return;
		void loadWizard();
		const timer = setInterval(async () => {
			if (leftSetup) return;
			try {
				const state = await fetchSetupState();
				if (state.status !== 'setup') {
					leftSetup = true;
					await setupStateStore.refresh();
					void goto('/', { replaceState: true });
					return;
				}
				if (state.launch) {
					launchState = state.launch;
					if (state.launch.status === 'running' && !launchPollTimer) {
						startLaunchPolling();
					}
				}
			} catch {
				// ignore transient poll errors
			}
		}, 8000);
		return () => {
			clearInterval(timer);
			stopLaunchPolling();
			if (identityDraftTimer) clearTimeout(identityDraftTimer);
		};
	});
</script>

<svelte:head>
	<title>Setup {$realmName || 'Realm'}</title>
</svelte:head>

<div class="setup-wizard" class:setup-wizard--welcome={isWelcomeStep}>
	{#if isWelcomeStep}
		<div class="setup-wizard__ambient" aria-hidden="true">
			<span class="setup-wizard__ambient-glow"></span>
			<span class="setup-wizard__ambient-grid"></span>
			<svg class="setup-wizard__ambient-rings" viewBox="0 0 600 600">
				<g class="setup-wizard__ambient-spin">
					<polygon points="570,300 435,533.8 165,533.8 30,300 165,66.2 435,66.2" />
					<circle cx="300" cy="300" r="248" />
					<line x1="30" y1="300" x2="570" y2="300" />
					<line x1="165" y1="66.2" x2="435" y2="533.8" />
				</g>
				<g class="setup-wizard__ambient-spin setup-wizard__ambient-spin--reverse">
					<polygon points="473.2,400 300,500 126.8,400 126.8,200 300,100 473.2,200" />
					<circle cx="300" cy="300" r="176" />
					<line x1="300" y1="30" x2="300" y2="570" />
					<line x1="165" y1="533.8" x2="435" y2="66.2" />
				</g>
				<g class="setup-wizard__ambient-spin setup-wizard__ambient-spin--slow">
					<rect x="148" y="148" width="304" height="304" />
					<circle cx="300" cy="300" r="118" />
					<polygon points="300,62 538,300 300,538 62,300" />
				</g>
				<g class="setup-wizard__ambient-spin setup-wizard__ambient-spin--slow-reverse">
					<polygon points="512,212 388,512 88,388 212,88" />
					<circle cx="300" cy="300" r="300" />
					<line x1="88" y1="88" x2="512" y2="512" />
					<line x1="512" y1="88" x2="88" y2="512" />
				</g>
			</svg>
		</div>
	{/if}
	<div class="setup-wizard__shell" class:setup-wizard__shell--welcome={isWelcomeStep}>
		{#if !isWelcomeStep}
			<header class="setup-wizard__header">
				<img src="/images/logo_sphere_only.svg" alt="" class="setup-wizard__mark" />
				<div>
					<p class="setup-wizard__eyebrow">Realm setup</p>
					<Heading tag="h1" class="setup-wizard__title">Configure {$realmName || 'your realm'}</Heading>
				</div>
			</header>

			<nav class="setup-wizard__steps" aria-label="Setup steps">
				{#each steps as step, index (step.id)}
					{#if index > 0}
						<span
							class="setup-wizard__step-rail"
							class:setup-wizard__step-rail--done={index <= stepIndex}
							aria-hidden="true"
						></span>
					{/if}
					<button
						type="button"
						class="setup-wizard__step"
						class:setup-wizard__step--active={step.id === currentStep}
						class:setup-wizard__step--done={index < stepIndex}
						class:setup-wizard__step--pending={index > stepIndex}
						aria-current={step.id === currentStep ? 'step' : undefined}
						onclick={() => goToStep(step.id)}
					>
						<span class="setup-wizard__step-index">
							{#if index < stepIndex}
								<svg viewBox="0 0 16 16" aria-hidden="true">
									<path
										d="M3.5 8.5 6.5 11.5 12.5 4.5"
										fill="none"
										stroke="currentColor"
										stroke-width="1.8"
										stroke-linecap="round"
										stroke-linejoin="round"
									/>
								</svg>
							{:else}
								{index + 1}
							{/if}
						</span>
						{step.label}
					</button>
				{/each}
			</nav>
		{/if}

		{#if loading}
			<P>Loading setup wizard…</P>
		{:else}
			{#if error}
				<div class="setup-wizard__error" role="alert">{error}</div>
			{/if}

			{#key currentStep}
			{#if currentStep === 'welcome'}
				<section class="setup-wizard__panel setup-wizard__panel--welcome setup-wizard__hero">
					<h1 class="setup-wizard__hero-title">
						{$realmName || 'Your realm'}
					</h1>
					<p class="setup-wizard__hero-lead">
						{WELCOME_FOUNDING_LINE}
					</p>
					<div class="setup-wizard__actions setup-wizard__actions--welcome">
						<button
							type="button"
							class="setup-wizard__hero-cta"
							disabled={busy}
							onclick={handleWelcomeContinue}
						>
							{busy ? 'Continuing…' : 'Begin'}
						</button>
					</div>
				</section>
			{:else if currentStep === 'codex'}
				<section class="setup-wizard__panel">
					<Heading tag="h2" class="text-xl font-semibold">Choose a codex</Heading>
					<P class="text-gray-600">Pick the governance package that defines how this realm runs.</P>

					<div class="setup-wizard__codex-list">
						{#each codices as codex (codex.id)}
							{@const description = codexDescriptions[codex.id] ?? codex.description ?? ''}
							{@const expanded = codexDescriptionExpanded[codex.id] ?? false}
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
								<div class="setup-wizard__codex-card-body">
									<div class="setup-wizard__codex-card-head">
										<strong>{codex.name || codex.id}</strong>
										{#if selectedCodexId === codex.id && codex.versions.length > 0}
											<label class="setup-wizard__codex-version">
												<span>Version</span>
												<select
													class="setup-wizard__version-select setup-wizard__version-select--inline"
													bind:value={selectedVersion}
													onclick={(event) => event.stopPropagation()}
												>
													{#each codex.versions as version (version)}
														<option value={version}>{version}</option>
													{/each}
												</select>
											</label>
										{/if}
									</div>
									{#if description}
										<p
											class="setup-wizard__codex-description text-sm text-gray-600"
											class:setup-wizard__codex-description--expanded={expanded}
										>
											{description}
										</p>
										{#if description.length > 160}
											<button
												type="button"
												class="setup-wizard__codex-description-toggle"
												onclick={(event) => {
													event.preventDefault();
													toggleCodexDescription(codex.id);
												}}
											>
												{expanded ? 'Show less' : 'Show more'}
											</button>
										{/if}
									{/if}
									<a
										href={codexRepositoryHref(codex)}
										class="setup-wizard__codex-repo"
										target="_blank"
										rel="noopener noreferrer"
										onclick={(event) => event.stopPropagation()}
									>
										Official repository
									</a>
								</div>
							</label>
						{/each}
					</div>

					<div class="setup-wizard__actions">
						{#if previousStep}
							<Button color="none" class={secondaryButtonClass} disabled={busy} onclick={goBack}>
								Back
							</Button>
						{/if}
						<Button
							color="none"
							class={primaryButtonClass}
							disabled={codexPrimaryDisabled}
							onclick={handleCodexContinue}
						>
							{codexPrimaryLabel}
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
					<div class="setup-wizard__field">
						<Label for="token-canister">Token canister ID (optional)</Label>
						<Input
							id="token-canister"
							bind:value={tokenCanisterId}
							placeholder="Existing ledger canister principal"
						/>
					</div>
					<div class="setup-wizard__actions">
						{#if previousStep}
							<Button color="none" class={secondaryButtonClass} disabled={busy} onclick={goBack}>
								Back
							</Button>
						{/if}
						<Button color="none" class={secondaryButtonClass} disabled={busy} onclick={skipStep}>
							Skip
						</Button>
						<Button color="none" class={primaryButtonClass} disabled={busy} onclick={handleTokenSave}>
							{busy ? 'Continuing…' : 'Continue'}
						</Button>
					</div>
				</section>
			{:else if currentStep === 'branding'}
				<section class="setup-wizard__panel setup-wizard__panel--branding">
					<div>
						<Heading tag="h2" class="text-xl font-semibold">Branding</Heading>
						<P class="text-gray-600">
							Write the realm's voice first. Then generate a mark, or upload your own.
						</P>

						<div class="setup-wizard__field">
							<Label for="welcome-message">Welcome message</Label>
							<textarea
								id="welcome-message"
								class="setup-wizard__textarea"
								bind:value={welcomeMessage}
								oninput={() => {
									welcomeMessageTouched = true;
									scheduleIdentityDraftSave();
								}}
								onblur={scheduleIdentityDraftSave}
								placeholder="A short greeting shown under the realm name"
								rows="3"
								maxlength={WELCOME_MESSAGE_MAX + 64}
							></textarea>
							<p
								class="setup-wizard__char-count"
								class:setup-wizard__char-count--over={welcomeMessageOverLimit}
							>
								{welcomeMessage.length} / {WELCOME_MESSAGE_MAX}
							</p>
						</div>
						<div class="setup-wizard__field">
							<Label for="manifesto">Manifesto</Label>
							<textarea
								id="manifesto"
								class="setup-wizard__textarea"
								bind:value={manifesto}
								oninput={() => {
									manifestoTouched = true;
									scheduleIdentityDraftSave();
								}}
								onblur={scheduleIdentityDraftSave}
								placeholder="What this realm stands for"
								rows="4"
								maxlength={MANIFESTO_MAX + 32}
							></textarea>
							<p
								class="setup-wizard__char-count"
								class:setup-wizard__char-count--over={manifestoOverLimit}
							>
								{manifesto.length} / {MANIFESTO_MAX}
							</p>
						</div>
						{#if brandingTextInvalid}
							<p class="setup-wizard__field-error" role="alert">
								{#if welcomeMessageOverLimit}
									Welcome message exceeds {WELCOME_MESSAGE_MAX} characters.
								{:else}
									Manifesto exceeds {MANIFESTO_MAX} characters.
								{/if}
							</p>
						{/if}

						<div class="setup-wizard__source" role="tablist" aria-label="Branding source">
							<button
								type="button"
								class="setup-wizard__source-btn"
								class:setup-wizard__source-btn--active={brandingSource === 'generate'}
								onclick={() => (brandingSource = 'generate')}
							>
								Generate
							</button>
							<button
								type="button"
								class="setup-wizard__source-btn"
								class:setup-wizard__source-btn--active={brandingSource === 'upload'}
								onclick={() => (brandingSource = 'upload')}
							>
								Upload
							</button>
						</div>

						{#if brandingSource === 'generate'}
							<div class="setup-wizard__generate">
								<button
									type="button"
									class="setup-wizard__hero-cta setup-wizard__generate-btn"
									disabled={busy || generatingBranding}
									onclick={generateBrandingFromIdentity}
								>
									{generatingBranding ? 'Composing…' : 'Generate'}
								</button>
								<p class="setup-wizard__generate-hint">
									Each press draws a new random mark and backdrop from the realm name and manifesto.
								</p>
							</div>
						{:else}
							<div class="setup-wizard__uploads">
								<BrandingDropzone label="Logo" preview={logoPreview} onFile={onLogoFile} />
								<BrandingDropzone
									label="Background"
									preview={backgroundPreview}
									onFile={onBackgroundFile}
								/>
							</div>
						{/if}

						<div class="setup-wizard__field">
							<Label for="primary-color">Primary color</Label>
							<Input id="primary-color" type="color" bind:value={primaryColor} class="h-11 w-24 p-1" />
						</div>

						<div class="setup-wizard__actions">
							{#if previousStep}
								<Button color="none" class={secondaryButtonClass} disabled={busy} onclick={goBack}>
									Back
								</Button>
							{/if}
							<Button color="none" class={secondaryButtonClass} disabled={busy} onclick={skipStep}>
								Skip
							</Button>
							<Button
								color="none"
								class={primaryButtonClass}
								disabled={busy || brandingTextInvalid}
								onclick={handleBrandingSave}
							>
								{busy ? 'Continuing…' : 'Continue'}
							</Button>
						</div>
					</div>

					<div class="setup-wizard__preview-wrap">
						<p class="setup-wizard__preview-label">Public dashboard preview</p>
						<PublicDashboardPreview
							logoPreview={logoPreview}
							backgroundPreview={backgroundPreview}
							welcomeMessage={welcomeMessage}
							manifesto={manifesto}
							realmName={$realmName || 'Your realm'}
						/>
					</div>
				</section>
			{:else}
				<section class="setup-wizard__panel">
					<Heading tag="h2" class="text-xl font-semibold">Review & launch</Heading>
					<P class="text-gray-600">Confirm your choices, then launch the realm into alpha.</P>

					<dl class="setup-wizard__summary">
						<div>
							<dt>Codex</dt>
							<dd>{summaryCodexPackage || 'Not chosen'}</dd>
						</div>
						<div>
							<dt>Codex version</dt>
							<dd>{summaryCodexVersion || '—'}</dd>
						</div>
						<div>
							<dt>Token</dt>
							<dd>{summaryTokenSymbol || 'Skipped'}</dd>
						</div>
						<div>
							<dt>Branding</dt>
							<dd>
								{#if hasBrandingDraft}
									Logo {logoPreview ? '✓' : '—'}, background {backgroundPreview ? '✓' : '—'},
									color {primaryColor}
								{:else}
									Skipped
								{/if}
							</dd>
						</div>
						<div>
							<dt>Welcome message</dt>
							<dd>{welcomeMessage.trim() || 'Default'}</dd>
						</div>
						<div>
							<dt>Manifesto</dt>
							<dd>{manifesto.trim() || 'Skipped'}</dd>
						</div>
					</dl>

					{#if launchState && !launchIdle}
						<ol class="setup-wizard__launch-steps" aria-label="Launch progress">
							{#each LAUNCH_PHASES as phase (phase.name)}
								{@const status = launchStepStatus(phase.name)}
								{@const stepError = launchStepError(phase.name)}
								<li
									class="setup-wizard__launch-step"
									class:setup-wizard__launch-step--pending={status === 'pending'}
									class:setup-wizard__launch-step--running={status === 'running'}
									class:setup-wizard__launch-step--completed={status === 'completed'}
									class:setup-wizard__launch-step--failed={status === 'failed'}
								>
									<span class="setup-wizard__launch-step-label">{phase.label}</span>
									<span class="setup-wizard__launch-step-status">
										{#if status === 'running'}
											Running…
										{:else if status === 'completed'}
											Done
										{:else if status === 'failed'}
											Failed
										{:else}
											Pending
										{/if}
									</span>
									{#if status === 'failed' && stepError}
										<p class="setup-wizard__launch-step-error" role="alert">{stepError}</p>
									{/if}
								</li>
							{/each}
						</ol>
					{/if}

					<div class="setup-wizard__actions">
						{#if previousStep && !launchRunning}
							<Button color="none" class={secondaryButtonClass} disabled={busy} onclick={goBack}>
								Back
							</Button>
						{/if}
						{#if launchFailed}
							<Button color="none" class={primaryButtonClass} disabled={busy} onclick={handleLaunch}>
								{busy ? 'Retrying…' : 'Retry launch'}
							</Button>
						{:else if launchCompleted}
							<Button color="none" class={primaryButtonClass} disabled>
								Launch complete
							</Button>
						{:else if launchRunning}
							<Button color="none" class={primaryButtonClass} disabled>
								Launching…
							</Button>
						{:else}
							<Button
								color="none"
								class={primaryButtonClass}
								disabled={busy || !summaryCodexPackage}
								onclick={handleLaunch}
							>
								{busy ? 'Starting…' : 'Launch realm'}
							</Button>
						{/if}
					</div>
				</section>
			{/if}
			{/key}
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

	:global(.dark) .setup-wizard {
		background: #0f172a;
	}

	.setup-wizard--welcome {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 2rem 1.25rem;
		position: relative;
		overflow: hidden;
		background: #ffffff;
	}

	:global(.dark) .setup-wizard--welcome {
		background: #080d1a;
	}

	.setup-wizard__ambient {
		position: absolute;
		inset: 0;
		overflow: hidden;
		pointer-events: none;
	}

	.setup-wizard__ambient-glow {
		position: absolute;
		top: -12%;
		left: 50%;
		width: min(52rem, 125vw);
		height: min(52rem, 125vw);
		transform: translateX(-50%);
		border-radius: 50%;
		background: radial-gradient(
			circle,
			rgba(99, 102, 241, 0.13) 0%,
			rgba(56, 189, 248, 0.07) 38%,
			transparent 68%
		);
	}

	/* Oversized and inset so the rotation never exposes an edge. */
	.setup-wizard__ambient-grid {
		position: absolute;
		inset: -45%;
		background-image:
			linear-gradient(to right, rgba(15, 23, 42, 0.05) 1px, transparent 1px),
			linear-gradient(to bottom, rgba(15, 23, 42, 0.05) 1px, transparent 1px);
		background-size: 72px 72px;
		animation: setup-ambient-drift 36s linear infinite;
		-webkit-mask-image: radial-gradient(ellipse at 50% 45%, #000 0%, transparent 70%);
		mask-image: radial-gradient(ellipse at 50% 45%, #000 0%, transparent 70%);
	}

	:global(.dark) .setup-wizard__ambient-grid {
		background-image:
			linear-gradient(to right, rgba(148, 163, 184, 0.07) 1px, transparent 1px),
			linear-gradient(to bottom, rgba(148, 163, 184, 0.07) 1px, transparent 1px);
	}

	.setup-wizard__ambient-rings {
		position: absolute;
		top: 50%;
		left: 50%;
		width: min(46rem, 118vw);
		height: min(46rem, 118vw);
		transform: translate(-50%, -50%);
	}

	.setup-wizard__ambient-rings polygon,
	.setup-wizard__ambient-rings circle,
	.setup-wizard__ambient-rings rect,
	.setup-wizard__ambient-rings line {
		fill: none;
		stroke: rgba(15, 23, 42, 0.055);
		stroke-width: 1;
	}

	:global(.dark) .setup-wizard__ambient-rings polygon,
	:global(.dark) .setup-wizard__ambient-rings circle,
	:global(.dark) .setup-wizard__ambient-rings rect,
	:global(.dark) .setup-wizard__ambient-rings line {
		stroke: rgba(148, 163, 184, 0.08);
	}

	.setup-wizard__ambient-spin {
		transform-origin: 300px 300px;
		animation: setup-ambient-rotate 80s linear infinite;
	}

	.setup-wizard__ambient-spin--reverse {
		animation-duration: 110s;
		animation-direction: reverse;
	}

	.setup-wizard__ambient-spin--slow {
		animation-duration: 130s;
	}

	.setup-wizard__ambient-spin--slow-reverse {
		animation-duration: 150s;
		animation-direction: reverse;
	}

	/* One full cell, so the loop has no visible seam. */
	@keyframes setup-ambient-drift {
		from {
			transform: rotate(-12deg) translate3d(0, 0, 0);
		}
		to {
			transform: rotate(-12deg) translate3d(72px, 72px, 0);
		}
	}

	@keyframes setup-ambient-rotate {
		from {
			transform: rotate(0deg);
		}
		to {
			transform: rotate(360deg);
		}
	}

	@media (prefers-reduced-motion: reduce) {
		.setup-wizard__ambient-grid,
		.setup-wizard__ambient-spin {
			animation: none;
		}
	}

	.setup-wizard__shell {
		max-width: 1100px;
		margin: 0 auto;
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 1rem;
		padding: 1.5rem;
		box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
	}

	:global(.dark) .setup-wizard__shell {
		background: #1e293b;
		border-color: #334155;
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
	}

	.setup-wizard__shell--welcome {
		width: 100%;
		max-width: 42rem;
		border: none;
		box-shadow: none;
		background: transparent;
		padding: 0;
		position: relative;
		z-index: 1;
	}

	:global(.dark) .setup-wizard__shell--welcome {
		background: transparent;
		border: none;
		box-shadow: none;
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

	:global(.dark) .setup-wizard__eyebrow {
		color: #94a3b8;
	}

	:global(.setup-wizard__title) {
		font-size: 1.5rem;
		font-weight: 600;
	}

	.setup-wizard__steps {
		display: flex;
		align-items: center;
		margin-bottom: 1.75rem;
	}

	.setup-wizard__step-rail {
		flex: 1 1 1.25rem;
		height: 1px;
		min-width: 0.75rem;
		background: #e2e8f0;
	}

	.setup-wizard__step-rail--done {
		background: #0b1120;
	}

	:global(.dark) .setup-wizard__step-rail {
		background: #334155;
	}

	:global(.dark) .setup-wizard__step-rail--done {
		background: #e2e8f0;
	}

	.setup-wizard__step {
		display: inline-flex;
		align-items: center;
		gap: 0.45rem;
		border: none;
		background: transparent;
		color: #94a3b8;
		padding: 0.15rem 0.15rem;
		font-size: 0.8125rem;
		white-space: nowrap;
		cursor: pointer;
	}

	.setup-wizard__step--done {
		color: #0b1120;
	}

	.setup-wizard__step--active {
		color: #0b1120;
		font-weight: 600;
	}

	.setup-wizard__step--pending {
		color: #94a3b8;
	}

	:global(.dark) .setup-wizard__step--done,
	:global(.dark) .setup-wizard__step--active {
		color: #f8fafc;
	}

	.setup-wizard__step-index {
		display: inline-flex;
		width: 1.5rem;
		height: 1.5rem;
		align-items: center;
		justify-content: center;
		border-radius: 999px;
		border: 1px solid #cbd5e1;
		background: #ffffff;
		font-size: 0.6875rem;
		flex-shrink: 0;
	}

	.setup-wizard__step-index svg {
		width: 0.8rem;
		height: 0.8rem;
	}

	.setup-wizard__step--done .setup-wizard__step-index {
		background: #0b1120;
		border-color: #0b1120;
		color: #ffffff;
	}

	.setup-wizard__step--active .setup-wizard__step-index {
		background: #ffffff;
		border-color: #0b1120;
		border-width: 2px;
		color: #0b1120;
	}

	:global(.dark) .setup-wizard__step-index {
		background: #0f172a;
		border-color: #475569;
		color: #94a3b8;
	}

	:global(.dark) .setup-wizard__step--done .setup-wizard__step-index {
		background: #e2e8f0;
		border-color: #e2e8f0;
		color: #0b1120;
	}

	:global(.dark) .setup-wizard__step--active .setup-wizard__step-index {
		background: #0f172a;
		border-color: #f8fafc;
		color: #f8fafc;
	}

	.setup-wizard__source {
		display: inline-flex;
		border: 1px solid #e2e8f0;
		border-radius: 999px;
		padding: 0.2rem;
		margin: 0.25rem 0 0.5rem;
	}

	.setup-wizard__source-btn {
		border: none;
		background: transparent;
		color: #64748b;
		border-radius: 999px;
		padding: 0.4rem 1rem;
		font: inherit;
		font-size: 0.875rem;
		cursor: pointer;
	}

	.setup-wizard__source-btn--active {
		background: #0b1120;
		color: #ffffff;
	}

	.setup-wizard__uploads {
		display: grid;
		gap: 0.85rem;
	}

	.setup-wizard__generate {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin: 0.5rem 0 0.25rem;
	}

	.setup-wizard__generate-btn {
		align-self: flex-start;
		padding: 0.7rem 1.4rem;
	}

	.setup-wizard__generate-hint {
		margin: 0;
		font-size: 0.8125rem;
		color: #64748b;
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
		min-height: 8.5rem;
	}

	.setup-wizard__codex-card--selected {
		border-color: #475569;
		background: #f8fafc;
	}

	.setup-wizard__codex-card-body {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
		flex: 1;
		min-width: 0;
	}

	.setup-wizard__codex-card-head {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.75rem;
	}

	.setup-wizard__codex-version {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		font-size: 0.75rem;
		color: #64748b;
		flex-shrink: 0;
	}

	.setup-wizard__version-select--inline {
		width: auto;
		min-width: 6.5rem;
		padding: 0.35rem 0.5rem;
		font-size: 0.8125rem;
	}

	.setup-wizard__codex-description {
		display: -webkit-box;
		-webkit-box-orient: vertical;
		-webkit-line-clamp: 3;
		overflow: hidden;
		margin: 0;
	}

	.setup-wizard__codex-description--expanded {
		display: block;
		-webkit-line-clamp: unset;
		overflow: visible;
	}

	.setup-wizard__codex-description-toggle {
		align-self: flex-start;
		border: none;
		background: none;
		color: #475569;
		font-size: 0.8125rem;
		padding: 0;
		cursor: pointer;
		text-decoration: underline;
	}

	.setup-wizard__codex-repo {
		margin-top: auto;
		font-size: 0.8125rem;
		color: #2563eb;
		text-decoration: underline;
	}

	.setup-wizard__panel--welcome {
		align-items: center;
		text-align: center;
		padding: 0;
		max-width: none;
	}

	.setup-wizard__hero {
		gap: 0;
	}

	.setup-wizard__hero-title {
		font-family: Fraunces, Georgia, 'Times New Roman', serif;
		font-size: clamp(2.75rem, 8vw, 5rem);
		font-weight: 400;
		line-height: 1.05;
		letter-spacing: -0.03em;
		color: #0b1120;
		margin: 0 0 1.5rem;
		animation: setup-welcome-fade-in 0.6s ease-out 0.08s both;
	}

	:global(.dark) .setup-wizard__hero-title {
		color: #f8fafc;
	}

	.setup-wizard__hero-lead {
		color: #5b6478;
		font-size: clamp(1rem, 2.4vw, 1.1875rem);
		font-weight: 300;
		line-height: 1.75;
		max-width: 35rem;
		margin: 0 auto;
		animation: setup-welcome-fade-in 0.6s ease-out 0.16s both;
	}

	.setup-wizard__hero-cta {
		display: inline-block;
		padding: 1rem 3.5rem;
		border-radius: 999px;
		border: 1.5px solid #0b1120;
		background: transparent;
		color: #0b1120;
		font-family: inherit;
		font-size: 1rem;
		font-weight: 500;
		cursor: pointer;
		transition:
			background-color 0.2s ease,
			color 0.2s ease;
	}

	.setup-wizard__hero-cta:hover:not(:disabled) {
		background: #0b1120;
		color: #ffffff;
	}

	.setup-wizard__hero-cta:disabled {
		opacity: 0.55;
		cursor: not-allowed;
	}

	:global(.dark) .setup-wizard__hero-cta {
		border-color: #e2e8f0;
		color: #e2e8f0;
	}

	:global(.dark) .setup-wizard__hero-cta:hover:not(:disabled) {
		background: #e2e8f0;
		color: #0b1120;
	}

	:global(.dark) .setup-wizard__hero-lead {
		color: #94a3b8;
	}

	/* Outranks the later, equally specific .setup-wizard__actions margin. */
	.setup-wizard__hero .setup-wizard__actions--welcome {
		margin-top: 3.25rem;
		justify-content: center;
		animation: setup-welcome-rise 0.55s ease-out 0.24s both;
	}

	@keyframes setup-welcome-fade-in {
		from {
			opacity: 0;
		}
		to {
			opacity: 1;
		}
	}

	@keyframes setup-welcome-rise {
		from {
			opacity: 0;
			transform: translateY(0.5rem);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.setup-wizard__field {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}

	.setup-wizard__version-select {
		display: block;
		width: 100%;
		border: 1px solid #d1d5db;
		border-radius: 0.5rem;
		background: #f9fafb;
		color: #111827;
		font-size: 0.875rem;
		padding: 0.625rem 0.75rem;
	}

	:global(.dark) .setup-wizard__version-select {
		border-color: #475569;
		background: #0f172a;
		color: #f1f5f9;
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

	:global(.dark) .setup-wizard__error {
		background: #450a0a;
		border-color: #7f1d1d;
		color: #fca5a5;
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

	:global(.dark) .setup-wizard__summary dd {
		color: #f1f5f9;
	}

	.setup-wizard__launch-steps {
		display: grid;
		gap: 0.5rem;
		margin: 0;
		padding: 0;
		list-style: none;
	}

	.setup-wizard__launch-step {
		display: grid;
		grid-template-columns: 1fr auto;
		gap: 0.25rem 1rem;
		border: 1px solid #e2e8f0;
		border-radius: 0.5rem;
		padding: 0.75rem 1rem;
	}

	.setup-wizard__launch-step--running {
		border-color: #93c5fd;
		background: #eff6ff;
	}

	.setup-wizard__launch-step--completed {
		border-color: #86efac;
		background: #f0fdf4;
	}

	.setup-wizard__launch-step--failed {
		border-color: #fca5a5;
		background: #fef2f2;
	}

	.setup-wizard__launch-step-label {
		font-weight: 500;
		color: #0f172a;
	}

	.setup-wizard__launch-step-status {
		font-size: 0.875rem;
		color: #64748b;
	}

	.setup-wizard__launch-step-error {
		grid-column: 1 / -1;
		margin: 0;
		font-size: 0.875rem;
		color: #b91c1c;
	}

	.setup-wizard__textarea {
		display: block;
		width: 100%;
		border: 1px solid #d1d5db;
		border-radius: 0.5rem;
		background: #f9fafb;
		color: #111827;
		font-size: 0.875rem;
		line-height: 1.5;
		padding: 0.625rem 0.75rem;
		resize: vertical;
		min-height: 5rem;
	}

	:global(.dark) .setup-wizard__textarea {
		border-color: #475569;
		background: #0f172a;
		color: #f1f5f9;
	}

	.setup-wizard__char-count {
		font-size: 0.75rem;
		color: #64748b;
		text-align: right;
		margin: 0;
	}

	.setup-wizard__char-count--over {
		color: #b91c1c;
		font-weight: 600;
	}

	.setup-wizard__field-error {
		font-size: 0.875rem;
		color: #b91c1c;
		margin: 0;
	}

	.setup-wizard__preview-wrap {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		min-height: 360px;
	}

	.setup-wizard__preview-label {
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.04em;
		color: #64748b;
		margin: 0;
	}
</style>
