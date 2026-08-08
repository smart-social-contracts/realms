<script lang="ts">
	import { Button, P } from 'flowbite-svelte';
	import type { SetupGateVariant } from '$lib/setup/gateLogic';

	interface Props {
		variant: SetupGateVariant;
		realmName?: string;
	}

	let { variant, realmName = 'This realm' }: Props = $props();

	const title = $derived(
		variant === 'anonymous'
			? `${realmName} is being set up.`
			: `${realmName} is being set up by its creator.`
	);

	const description = $derived(
		variant === 'anonymous'
			? 'Check back soon. If you are the creator, sign in to continue setup.'
			: 'The creator is finishing initial configuration. Please check back later.'
	);
</script>

<svelte:head>
	<title>{title}</title>
</svelte:head>

<main class="setup-gate">
	<div class="setup-gate__card">
		<img src="/images/logo_sphere_only.svg" alt="" class="setup-gate__logo" />
		<h1>{title}</h1>
		<P class="setup-gate__text">{description}</P>
		{#if variant === 'anonymous'}
			<Button href="/join" color="blue" class="setup-gate__button">Log in</Button>
		{/if}
	</div>
</main>

<style>
	.setup-gate {
		display: flex;
		min-height: 100vh;
		min-height: 100dvh;
		align-items: center;
		justify-content: center;
		background: linear-gradient(160deg, #f8fafc 0%, #e2e8f0 100%);
		padding: 1.5rem;
	}

	.setup-gate__card {
		max-width: 32rem;
		width: 100%;
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 1rem;
		padding: 2rem;
		text-align: center;
		box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
	}

	.setup-gate__logo {
		width: 3.5rem;
		height: 3.5rem;
		margin: 0 auto 1rem;
		opacity: 0.85;
	}

	h1 {
		font-size: 1.5rem;
		font-weight: 600;
		color: #0f172a;
		margin-bottom: 0.75rem;
	}

	:global(.setup-gate__text) {
		color: #64748b;
		margin-bottom: 1.5rem;
	}

	:global(.setup-gate__button) {
		margin: 0 auto;
	}
</style>
