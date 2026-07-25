<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, Spinner } from 'flowbite-svelte';
	import { backend } from '$lib/canisters';

	interface ActivityEvent {
		title: string;
		description: string;
		date: string;
		rawDate: Date;
		icon: string;
		bgColor: string;
	}

	let activities: ActivityEvent[] = [];
	let loading = true;

	function parseEntities(response: any): any[] {
		if (response?.success && response?.data?.objectsListPaginated) {
			return (response.data.objectsListPaginated.objects || []).map((s: string) => JSON.parse(s));
		}
		return [];
	}

	function parseDate(ts: string): Date | null {
		if (!ts) return null;
		try {
			const d = new Date(ts.replace(' ', 'T'));
			if (isNaN(d.getTime())) return null;
			return d;
		} catch { return null; }
	}

	function formatDate(d: Date): string {
		const now = new Date();
		const diffMs = now.getTime() - d.getTime();
		const diffMin = Math.floor(diffMs / 60000);
		if (diffMin < 1) return 'Just now';
		if (diffMin < 60) return `${diffMin}m ago`;
		const diffHr = Math.floor(diffMin / 60);
		if (diffHr < 24) return `${diffHr}h ago`;
		const diffDay = Math.floor(diffHr / 24);
		if (diffDay < 30) return `${diffDay}d ago`;
		return d.toLocaleDateString('en', { year: 'numeric', month: 'short', day: 'numeric' });
	}

	function addEvents(entities: any[], title: string, icon: string, bgColor: string, descFn: (e: any) => string, events: ActivityEvent[]) {
		for (const e of entities) {
			const d = parseDate(e.timestamp_created);
			if (d) events.push({ title, description: descFn(e), date: formatDate(d), rawDate: d, icon, bgColor });
		}
	}

	async function loadActivity() {
		loading = true;
		try {
			const [usersResp, orgsResp, proposalsResp, transfersResp, votesResp, landsResp, courtsResp, licensesResp] = await Promise.all([
				backend.get_objects_paginated("User", 0, 5, "desc"),
				backend.get_objects_paginated("Organization", 0, 5, "desc"),
				backend.get_objects_paginated("Proposal", 0, 5, "desc"),
				backend.get_objects_paginated("Transfer", 0, 5, "desc"),
				backend.get_objects_paginated("Vote", 0, 5, "desc"),
				backend.get_objects_paginated("Land", 0, 5, "desc"),
				backend.get_objects_paginated("Court", 0, 5, "desc"),
				backend.get_objects_paginated("License", 0, 5, "desc"),
			]);

			const events: ActivityEvent[] = [];

			addEvents(parseEntities(usersResp), 'New member joined', '👤', 'bg-blue-100', (u) => u.name || u.id?.substring(0, 12) || 'Unknown', events);
			addEvents(parseEntities(orgsResp), 'Organization created', '🏛', 'bg-purple-100', (o) => o.name || 'Unnamed', events);
			addEvents(parseEntities(proposalsResp), 'Proposal submitted', '📋', 'bg-amber-100', (p) => p.title || p.name || 'Untitled', events);
			addEvents(parseEntities(transfersResp), 'Token transfer', '💰', 'bg-green-100', (t) => `${t.amount ? Number(t.amount).toLocaleString() : '?'} tokens`, events);
			addEvents(parseEntities(votesResp), 'Vote cast', '🗳', 'bg-rose-100', (v) => v.choice || 'on a proposal', events);
			addEvents(parseEntities(landsResp), 'Land registered', '🗺', 'bg-emerald-100', (l) => l.name || l.location || 'New parcel', events);
			addEvents(parseEntities(courtsResp), 'Court case', '⚖', 'bg-orange-100', (c) => c.name || c.title || 'New case', events);
			addEvents(parseEntities(licensesResp), 'License issued', '📜', 'bg-cyan-100', (l) => l.name || l.title || 'New license', events);

			events.sort((a, b) => b.rawDate.getTime() - a.rawDate.getTime());
			activities = events.slice(0, 20);
		} catch (error) {
			console.error('Error loading activity:', error);
		}
		loading = false;
	}

	onMount(loadActivity);
</script>

<Card size="xl" class="!p-6">
	<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Latest Activity</h3>
	{#if loading}
		<div class="flex items-center justify-center py-8">
			<Spinner size="6" />
			<span class="ml-3 text-gray-400 text-sm">Loading activity...</span>
		</div>
	{:else if activities.length === 0}
		<div class="flex items-center justify-center py-8">
			<p class="text-gray-400">No recent activity</p>
		</div>
	{:else}
		<div class="divide-y divide-gray-100">
			{#each activities as event}
				<div class="flex items-center gap-3 py-2.5">
					<div class="flex-shrink-0 w-8 h-8 rounded-full {event.bgColor} flex items-center justify-center text-sm">
						{event.icon}
					</div>
					<div class="flex-1 min-w-0">
						<span class="text-sm font-medium text-gray-900">{event.title}</span>
						<span class="text-sm text-gray-500 ml-1">— {event.description}</span>
					</div>
					<span class="flex-shrink-0 text-xs text-gray-400 whitespace-nowrap">{event.date}</span>
				</div>
			{/each}
		</div>
	{/if}
</Card>
