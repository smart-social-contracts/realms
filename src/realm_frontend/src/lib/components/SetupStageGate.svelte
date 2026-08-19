<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { browser } from '$app/environment';
	import { get } from 'svelte/store';
	import { backendActorReady } from '$lib/canisters';
	import { restoreAuthSession, resetAuthSessionRestore } from '$lib/auth';
	import { isAuthenticated } from '$lib/stores/auth';
	import { realmName, realmInfo } from '$lib/stores/realmInfo';
	import { setupStateStore } from '$lib/stores/setupState';
	import {
		MAX_UNKNOWN_SETUP_ATTEMPTS,
		resolveSetupGate,
		shouldPollSetupState
	} from '$lib/setup/gateLogic';
	import SetupGatePage from '$lib/components/SetupGatePage.svelte';

	let uiReadySignalled = false;

	interface Props {
		children: import('svelte').Snippet;
	}

	let { children }: Props = $props();

	let authChannelSettled = $state(false);
	let setupStateLoaded = $state(false);
	let pollTimer: ReturnType<typeof setInterval> | undefined;
	let probeTimer: ReturnType<typeof setInterval> | undefined;
	let redirectedToSetup = $state(false);
	let unknownStatusFailures = $state(0);
	let showStillWorking = $state(false);
	let stillWorkingTimer: ReturnType<typeof setTimeout> | undefined;
	let loadingTimerStarted = false;

	const gateInput = $derived({
		loading: $setupStateStore.loading,
		status: $setupStateStore.state?.status ?? null,
		unknownStatusFailures,
		isAuthenticated: $isAuthenticated,
		isCallerAuthorized: $setupStateStore.state?.is_caller_authorized ?? false,
		authChannelSettled,
		setupStateLoaded,
		pathname: $page.url.pathname
	});

	const decision = $derived(resolveSetupGate(gateInput));
	const onSetupWizard = $derived(
		$setupStateStore.state?.status === 'setup' &&
			$setupStateStore.state?.is_caller_authorized &&
			($page.url.pathname === '/setup' || $page.url.pathname.startsWith('/setup/'))
	);

	$effect(() => {
		if (decision.kind !== 'loading') {
			if (stillWorkingTimer) {
				clearTimeout(stillWorkingTimer);
				stillWorkingTimer = undefined;
			}
			showStillWorking = false;
			loadingTimerStarted = false;
			return;
		}

		if (!loadingTimerStarted) {
			loadingTimerStarted = true;
			stillWorkingTimer = setTimeout(() => {
				showStillWorking = true;
			}, 6000);
		}
	});

	$effect(() => {
		if (decision.kind === 'loading' || decision.kind === 'redirect' || uiReadySignalled) return;
		uiReadySignalled = true;
		void (async () => {
			await tick();
			const { portalUiReady } = await import('$lib/portal-bridge');
			portalUiReady();
		})();
	});

	onDestroy(() => {
		if (stillWorkingTimer) clearTimeout(stillWorkingTimer);
	});

	async function refreshSetupState() {
		try {
			const state = await setupStateStore.refresh();
			setupStateLoaded = true;
			unknownStatusFailures = 0;
			if (state.status !== 'setup' && browser) {
				const path = get(page).url.pathname;
				if (path === '/setup' || path.startsWith('/setup/')) {
					void goto('/', { replaceState: true });
				}
			}
			return state;
		} catch {
			setupStateLoaded = true;
			unknownStatusFailures += 1;
			return null;
		}
	}

	async function settleAuthChannel() {
		const { isEmbeddedInPortal, waitForPortalDelegation } = await import('$lib/portal-bridge');
		await backendActorReady;
		await restoreAuthSession();

		if (isEmbeddedInPortal() && !get(isAuthenticated)) {
			await waitForPortalDelegation({ timeoutMs: 15_000 });
			resetAuthSessionRestore();
			await restoreAuthSession();
		}

		authChannelSettled = true;
	}

	async function handlePortalAuth() {
		resetAuthSessionRestore();
		await restoreAuthSession();
		await refreshSetupState();
	}

	onMount(() => {
		let cancelled = false;

		(async () => {
			await settleAuthChannel();
			if (cancelled) return;
			void realmInfo.fetch();
			await refreshSetupState();
			if (cancelled) return;

			while (
				!cancelled &&
				get(setupStateStore).state === null &&
				unknownStatusFailures > 0 &&
				unknownStatusFailures < MAX_UNKNOWN_SETUP_ATTEMPTS
			) {
				await new Promise((r) => setTimeout(r, 1_500));
				if (cancelled) return;
				await refreshSetupState();
			}
			if (cancelled) return;

			pollTimer = setInterval(() => {
				if (onSetupWizard) return;
				if (shouldPollSetupState(get(setupStateStore).state?.status ?? null)) {
					void refreshSetupState();
				}
			}, 8000);

			const { isEmbeddedInPortal, requestSilentAuthProbe } = await import('$lib/portal-bridge');
			probeTimer = setInterval(() => {
				if (cancelled || get(isAuthenticated) || !isEmbeddedInPortal()) return;
				requestSilentAuthProbe();
			}, 10_000);
		})();

		const onPortalAuth = () => {
			void handlePortalAuth();
		};
		window.addEventListener('portal:auth', onPortalAuth);

		return () => {
			cancelled = true;
			window.removeEventListener('portal:auth', onPortalAuth);
			if (pollTimer) clearInterval(pollTimer);
			if (probeTimer) clearInterval(probeTimer);
		};
	});

	$effect(() => {
		if (!browser || !authChannelSettled || !setupStateLoaded) return;
		if (decision.kind !== 'redirect') {
			redirectedToSetup = false;
			return;
		}
		if (redirectedToSetup) return;
		redirectedToSetup = true;
		void goto(decision.to, { replaceState: true });
	});
</script>

{#if decision.kind === 'loading'}
	<div class="setup-shell" role="status" aria-live="polite">
		<div class="setup-shell__header setup-shell__pulse" aria-hidden="true"></div>
		<div class="setup-shell__main">
			<div class="setup-shell__blocks" aria-hidden="true">
				<div class="setup-shell__block setup-shell__pulse"></div>
				<div class="setup-shell__block setup-shell__block--md setup-shell__pulse"></div>
				<div class="setup-shell__block setup-shell__block--sm setup-shell__pulse"></div>
			</div>
			<p class="setup-shell__label">Loading setup…</p>
			{#if showStillWorking}
				<p class="setup-shell__sublabel">Still working…</p>
			{/if}
		</div>
	</div>
{:else if decision.kind === 'gate'}
	<SetupGatePage variant={decision.variant} realmName={$realmName || 'This realm'} />
{:else}
	{@render children()}
{/if}

<style>
	.setup-shell {
		display: flex;
		flex-direction: column;
		min-height: 100vh;
		min-height: 100dvh;
		background: #ffffff;
	}

	.setup-shell__header {
		flex-shrink: 0;
		height: 56px;
		background: #e5e7eb;
	}

	.setup-shell__main {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 2rem 1.5rem;
		gap: 0.75rem;
	}

	.setup-shell__blocks {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		width: 100%;
		max-width: 28rem;
		margin-bottom: 0.5rem;
	}

	.setup-shell__block {
		height: 5rem;
		border-radius: 0.5rem;
		background: #f3f4f6;
	}

	.setup-shell__block--md {
		height: 3.5rem;
		background: #e5e7eb;
	}

	.setup-shell__block--sm {
		height: 2.5rem;
		width: 60%;
		background: #f3f4f6;
	}

	.setup-shell__pulse {
		animation: setup-shell-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
	}

	.setup-shell__label {
		margin: 0;
		font-size: 0.875rem;
		color: #64748b;
		text-align: center;
	}

	.setup-shell__sublabel {
		margin: 0;
		font-size: 0.75rem;
		color: #94a3b8;
		text-align: center;
	}

	@keyframes setup-shell-pulse {
		0%,
		100% {
			opacity: 1;
		}

		50% {
			opacity: 0.5;
		}
	}
</style>
