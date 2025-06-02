<script lang="ts">
	import { Button, Card, Timeline, TimelineItem } from 'flowbite-svelte';
	import { ArrowRightOutline } from 'flowbite-svelte-icons';

	// Mock activity data
	const activities = [
		{
			title: "New proposal submitted in ACME Corp",
			date: "10 minutes ago",
			description: "A new governance proposal for budget allocation has been submitted by alice@example.com. Voting period ends in 3 days.",
			actionText: "Review proposal",
			actionLink: "/proposal?id=prop-135"
		},
		{
			title: "Community DAO reached 150+ members",
			date: "2 hours ago",
			description: "Community DAO has grown to over 150 members, unlocking level 3 governance features with multi-signature capabilities.",
			actionText: "View organization",
			actionLink: "/organization?id=org-community-dao"
		},
		{
			title: "New token distribution completed",
			date: "Yesterday",
			description: "GREEN Token distribution to 42 members of GreenFuture organization has been completed successfully.",
			actionText: "View transaction details",
			actionLink: "/transactions"
		},
		{
			title: "DeFi Alliance proposal approved",
			date: "2 days ago",
			description: "Proposal #28 to integrate with external DeFi protocols has been approved with 82% votes in favor.",
			actionText: "See results",
			actionLink: "/proposal?id=prop-128"
		},
		{
			title: "System maintenance completed",
			date: "Jan 20, 2023",
			description: "Platform maintenance and security updates have been successfully deployed without any service disruption.",
			actionText: "View system status",
			actionLink: "/settings/system"
		}
	];
</script>

<Card size="xl">
	<div class="mb-4 flex items-center justify-between">
		<h3 class="text-lg font-semibold text-gray-900 dark:text-white">Latest Activity</h3>
		<a
			href="#top"
			class="inline-flex items-center rounded-lg p-2 text-sm font-medium text-primary-700 hover:bg-gray-100 dark:text-primary-500 dark:hover:bg-gray-700"
		>
			View all
		</a>
	</div>
	<Timeline>
		{#each activities as activity, index}
			<TimelineItem title={activity.title} date={activity.date}>
				<p class="mb-4 text-base font-normal text-gray-500 dark:text-gray-400">
					{activity.description}
				</p>
				<Button color="alternative" href={activity.actionLink}>
					{activity.actionText}<ArrowRightOutline class="ms-2" size="sm" />
				</Button>
			</TimelineItem>
		{/each}
	</Timeline>
</Card>
