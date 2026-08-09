<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { browser } from '$app/environment';
	import { get } from 'svelte/store';
	import { backendActorReady } from '$lib/canisters';
	import { restoreAuthSession, resetAuthSessionRestore } from '$lib/auth';
	import { isAuthenticated } from '$lib/stores/auth';
	import { realmName, realmInfo } from '$lib/stores/realmInfo';
	import { setupStateStore } from '$lib/stores/setupState';
	import { resolveSetupGate, shouldPollSetupState } from '$lib/setup/gateLogic';
	import SetupGatePage from '$lib/components/SetupGatePage.svelte';

	interface Props {
		children: import('svelte').Snippet;
	}

	let { children }: Props = $props();

	let authChannelSettled = $state(false);
	let setupStateLoaded = $state(false);
	let pollTimer: ReturnType<typeof setInterval> | undefined;
	let probeTimer: ReturnType<typeof setInterval> | undefined;
	let redirectedToSetup = $state(false);

	const gateInput = $derived({
		loading: $setupStateStore.loading,
		status: $setupStateStore.state?.status ?? null,
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

	async function refreshSetupState() {
		try {
			const state = await setupStateStore.refresh();
			setupStateLoaded = true;
			if (state.status !== 'setup' && browser) {
				const path = get(page).url.pathname;
				if (path === '/setup' || path.startsWith('/setup/')) {
					void goto('/', { replaceState: true });
				}
			}
			return state;
		} catch {
			setupStateLoaded = true;
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
	<div class="setup-stage-loading" role="status" aria-live="polite">
		<div class="setup-stage-loading__dots" aria-hidden="true">
			<span></span><span></span><span></span>
		</div>
		<p class="setup-stage-loading__label">Loading setup…</p>
	</div>
{:else if decision.kind === 'gate'}
	<SetupGatePage variant={decision.variant} realmName={$realmName || 'This realm'} />
{:else}
	{@render children()}
{/if}

<style>
	.setup-stage-loading {
		display: flex;
		flex-direction: column;
		min-height: 100vh;
		min-height: 100dvh;
		align-items: center;
		justify-content: center;
		gap: 1rem;
		background: #ffffff;
	}

	.setup-stage-loading__label {
		margin: 0;
		font-size: 0.9375rem;
		color: #64748b;
	}

	.setup-stage-loading__dots {
		display: flex;
		gap: 0.5rem;
	}

	.setup-stage-loading__dots span {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		background: #94a3b8;
		animation: setup-dot-pulse 1.4s ease-in-out infinite;
	}

	.setup-stage-loading__dots span:nth-child(2) {
		animation-delay: 0.2s;
	}

	.setup-stage-loading__dots span:nth-child(3) {
		animation-delay: 0.4s;
	}

	@keyframes setup-dot-pulse {
		0%,
		80%,
		100% {
			opacity: 0.3;
			transform: scale(0.8);
		}
		40% {
			opacity: 1;
			transform: scale(1);
		}
	}
</style>
