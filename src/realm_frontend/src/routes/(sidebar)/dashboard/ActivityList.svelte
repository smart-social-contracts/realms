<script lang="ts">
	import { onMount } from 'svelte';
	import { Button, Card, Spinner, Timeline, TimelineItem } from 'flowbite-svelte';
	import { ArrowRightOutline } from 'flowbite-svelte-icons';
	import { backend } from '$lib/canisters';

	let activities: any[] = [];
	let loading = true;

	function relativeTime(ts: string): string {
		if (!ts) return '';
		try {
			const d = new Date(ts.replace(' ', 'T'));
			const now = new Date();
			const diffMs = now.getTime() - d.getTime();
			const diffMin = Math.floor(diffMs / 60000);
			if (diffMin < 1) return 'Just now';
			if (diffMin < 60) return `${diffMin} minute${diffMin > 1 ? 's' : ''} ago`;
			const diffHr = Math.floor(diffMin / 60);
			if (diffHr < 24) return `${diffHr} hour${diffHr > 1 ? 's' : ''} ago`;
			const diffDay = Math.floor(diffHr / 24);
			if (diffDay < 30) return `${diffDay} day${diffDay > 1 ? 's' : ''} ago`;
			return d.toLocaleDateString('en', { year: 'numeric', month: 'short', day: 'numeric' });
		} catch {
			return ts;
		}
	}

	async function loadActivity() {
		loading = true;
		try {
			const response = await backend.get_objects_paginated("Notification", 0, 10, "desc");
			if (response?.success && response?.data?.objectsListPaginated) {
				const objects = response.data.objectsListPaginated.objects || [];
				activities = objects.map((s: string) => {
					const n = JSON.parse(s);
					return {
						title: n.title || 'Notification',
						date: relativeTime(n.timestamp_created),
						description: n.message || '',
						actionLink: n.href || '#',
					};
				});
			}
		} catch (error) {
			console.error('Error loading activity:', error);
		}
		loading = false;
	}

	onMount(loadActivity);
</script>

<Card size="xl">
	<div class="mb-4 flex items-center justify-between">
		<h3 class="text-lg font-semibold text-gray-900 dark:text-white">Latest Activity</h3>
	</div>
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
		<Timeline>
			{#each activities as activity}
				<TimelineItem title={activity.title} date={activity.date}>
					<p class="mb-4 text-base font-normal text-gray-500 dark:text-gray-400">
						{activity.description}
					</p>
					{#if activity.actionLink && activity.actionLink !== '#'}
						<Button color="alternative" href={activity.actionLink}>
							View details<ArrowRightOutline class="ms-2" size="sm" />
						</Button>
					{/if}
				</TimelineItem>
			{/each}
		</Timeline>
	{/if}
</Card>
