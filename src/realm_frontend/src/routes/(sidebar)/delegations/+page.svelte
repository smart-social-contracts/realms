<script lang="ts">
	import MetaTag from '../../utils/MetaTag.svelte';
	import { Button, Card, Heading, P, Spinner } from 'flowbite-svelte';
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { resolveDelegationBackend } from '$lib/stores/delegation.js';
	import { isAuthenticated } from '$lib/stores/auth';
	import {
		delegationsAsDelegate,
		delegationsAsGrantor,
		pendingDelegations,
		loadDelegations,
		setActingOnBehalfOf
	} from '$lib/stores/delegation.js';

	const path = '/delegations';
	const title = 'Delegations';
	const description = 'Manage Power of Attorney — act on behalf of other members';

	let loading = true;
	let message = '';
	let error = '';

	onMount(async () => {
		if (!$isAuthenticated) {
			loading = false;
			return;
		}
		await refresh();
		const acceptId = $page.url.searchParams.get('accept');
		if (acceptId) await acceptOne(acceptId);
	});

	async function refresh() {
		loading = true;
		error = '';
		await loadDelegations();
		loading = false;
	}

	async function acceptOne(delegationId: string) {
		error = '';
		message = '';
		try {
			const actor = await resolveDelegationBackend();
			const raw = await actor.accept_delegation_json(
				JSON.stringify({ delegation_id: delegationId })
			);
			const res = typeof raw === 'string' ? JSON.parse(raw) : raw;
			if (res.success) {
				message = 'Delegation accepted.';
				await refresh();
			} else {
				error = res.error || 'Accept failed';
			}
		} catch (e: any) {
			error = e.message || 'Accept failed';
		}
	}

	async function revokeOne(delegationId: string) {
		error = '';
		message = '';
		try {
			const actor = await resolveDelegationBackend();
			const raw = await actor.revoke_delegation_json(
				JSON.stringify({ delegation_id: delegationId })
			);
			const res = typeof raw === 'string' ? JSON.parse(raw) : raw;
			if (res.success) {
				message = 'Delegation revoked.';
				await refresh();
			} else {
				error = res.error || 'Revoke failed';
			}
		} catch (e: any) {
			error = e.message || 'Revoke failed';
		}
	}

	function scopeSummary(scope: { all?: boolean; operations?: string[] }) {
		if (scope?.all) return 'All operations (admin grantor only)';
		const ops = scope?.operations || [];
		return ops.length ? ops.join(', ') : '—';
	}

	function fmtExpiry(ts: number) {
		if (!ts) return 'No expiry';
		return new Date(ts * 1000).toLocaleString();
	}
</script>

<MetaTag {path} {title} {description} />

<div class="p-4 max-w-4xl mx-auto space-y-6">
	<Heading tag="h1" class="text-2xl font-bold">Delegations</Heading>
	<P class="text-gray-600">
		Power of Attorney lets you act on another member's behalf within a scoped set of
		permissions — without sharing private keys.
	</P>

	{#if message}
		<p class="text-green-700 text-sm">{message}</p>
	{/if}
	{#if error}
		<p class="text-red-600 text-sm">{error}</p>
	{/if}

	{#if loading}
		<Spinner />
	{:else if !$isAuthenticated}
		<P>Sign in to manage delegations.</P>
	{:else}
		<Card size="xl" class="shadow-sm">
			<Heading tag="h2" class="text-lg mb-3">Pending — accept to act on behalf</Heading>
			{#if $pendingDelegations.length === 0}
				<P class="text-gray-500 text-sm">No pending invitations.</P>
			{:else}
				<ul class="divide-y divide-gray-100">
					{#each $pendingDelegations as d (d.id)}
						<li class="py-3 flex flex-wrap items-center justify-between gap-2">
							<div>
								<p class="font-medium">{d.label || d.grantor}</p>
								<p class="text-xs text-gray-500">Scope: {scopeSummary(d.scope)}</p>
								<p class="text-xs text-gray-500">Expires: {fmtExpiry(d.expires_at)}</p>
							</div>
							<div class="flex gap-2">
								<Button size="sm" onclick={() => acceptOne(d.id)}>Accept</Button>
								<Button size="sm" color="light" onclick={() => revokeOne(d.id)}>Decline</Button>
							</div>
						</li>
					{/each}
				</ul>
			{/if}
		</Card>

		<Card size="xl" class="shadow-sm">
			<Heading tag="h2" class="text-lg mb-3">Granted to me (active)</Heading>
			{#if $delegationsAsDelegate.filter((d) => d.status === 'active').length === 0}
				<P class="text-gray-500 text-sm">None active.</P>
			{:else}
				<ul class="divide-y divide-gray-100">
					{#each $delegationsAsDelegate.filter((d) => d.status === 'active') as d (d.id)}
						<li class="py-3 flex flex-wrap items-center justify-between gap-2">
							<div>
								<p class="font-medium">{d.label || d.grantor}</p>
								<p class="text-xs text-gray-500">{scopeSummary(d.scope)}</p>
							</div>
							<div class="flex gap-2">
								<Button size="sm" color="alternative" onclick={() => setActingOnBehalfOf(d.grantor)}>
									Act as them
								</Button>
								<Button size="sm" color="light" onclick={() => revokeOne(d.id)}>Revoke</Button>
							</div>
						</li>
					{/each}
				</ul>
			{/if}
		</Card>

		<Card size="xl" class="shadow-sm">
			<Heading tag="h2" class="text-lg mb-3">Granted by me</Heading>
			{#if $delegationsAsGrantor.length === 0}
				<P class="text-gray-500 text-sm">You have not granted any delegations.</P>
			{:else}
				<ul class="divide-y divide-gray-100">
					{#each $delegationsAsGrantor as d (d.id)}
						<li class="py-3 flex flex-wrap items-center justify-between gap-2">
							<div>
								<p class="font-medium">→ {d.delegate}</p>
								<p class="text-xs text-gray-500">Status: {d.status} · {scopeSummary(d.scope)}</p>
							</div>
							{#if d.status === 'active' || d.status === 'pending'}
								<Button size="sm" color="light" onclick={() => revokeOne(d.id)}>Revoke</Button>
							{/if}
						</li>
					{/each}
				</ul>
			{/if}
		</Card>
	{/if}
</div>
