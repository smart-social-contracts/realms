<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { browser } from '$app/environment';
	import { get } from 'svelte/store';
	import { backendReady } from '$lib/canisters';
	import { restoreAuthSession } from '$lib/auth';
	import { isAuthenticated } from '$lib/stores/auth';
	import { realmName, realmInfo } from '$lib/stores/realmInfo';
	import { setupStateStore } from '$lib/stores/setupState';
	import { resolveSetupGate, shouldPollSetupState } from '$lib/setup/gateLogic';
	import SetupGatePage from '$lib/components/SetupGatePage.svelte';

	interface Props {
		children: import('svelte').Snippet;
	}

	let { children }: Props = $props();

	let authReady = $state(false);
	let pollTimer: ReturnType<typeof setInterval> | undefined;
	let probeTimer: ReturnType<typeof setInterval> | undefined;

	const gateInput = $derived({
		loading: !authReady || $setupStateStore.loading,
		status: $setupStateStore.state?.status ?? null,
		isAuthenticated: $isAuthenticated,
		isCallerAuthorized: $setupStateStore.state?.is_caller_authorized ?? false,
		pathname: $page.url.pathname
	});

	const decision = $derived(resolveSetupGate(gateInput));

	async function refreshSetupState() {
		try {
			const state = await setupStateStore.refresh();
			if (state.status !== 'setup' && browser) {
				const path = get(page).url.pathname;
				if (path === '/setup' || path.startsWith('/setup/')) {
					window.location.replace('/');
				}
			}
			return state;
		} catch {
			return null;
		}
	}

	onMount(() => {
		let cancelled = false;

		(async () => {
			await backendReady;
			await restoreAuthSession();
			void realmInfo.fetch();
			if (cancelled) return;
			authReady = true;
			await refreshSetupState();
			if (cancelled) return;

			pollTimer = setInterval(() => {
				if (shouldPollSetupState(get(setupStateStore).state?.status ?? null)) {
					void refreshSetupState();
				}
			}, 8000);

			// The initial silent delegation probe can be answered before the
			// portal host's session is ready (auth:pending), and nothing else
			// re-asks — leaving the gate stuck on "anonymous" for a signed-in
			// portal user. Re-probe silently until a delegation lands.
			const { isEmbeddedInPortal, requestSilentAuthProbe } = await import(
				'$lib/portal-bridge'
			);
			probeTimer = setInterval(() => {
				if (cancelled || get(isAuthenticated) || !isEmbeddedInPortal()) return;
				requestSilentAuthProbe();
			}, 10_000);
		})();

		return () => {
			cancelled = true;
			if (pollTimer) clearInterval(pollTimer);
			if (probeTimer) clearInterval(probeTimer);
		};
	});

	$effect(() => {
		if (!browser || !authReady) return;
		if (decision.kind === 'redirect') {
			void goto(decision.to, { replaceState: true });
		}
	});
</script>

{#if decision.kind === 'loading'}
	<div class="setup-stage-loading">
		<div class="setup-stage-loading__dots" aria-hidden="true">
			<span></span><span></span><span></span>
		</div>
	</div>
{:else if decision.kind === 'gate'}
	<SetupGatePage variant={decision.variant} realmName={$realmName || 'This realm'} />
{:else}
	{@render children()}
{/if}

<style>
	.setup-stage-loading {
		display: flex;
		min-height: 100vh;
		min-height: 100dvh;
		align-items: center;
		justify-content: center;
		background: #ffffff;
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
