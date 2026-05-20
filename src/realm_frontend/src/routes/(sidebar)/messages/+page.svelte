<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, Heading, Spinner } from 'flowbite-svelte';
	import { notifications, unreadCount, loadNotifications, markAsRead } from '$lib/stores/notifications';
	import { IconMail, IconMailOpened, IconInbox } from '@tabler/icons-svelte';

	let loading = true;
	let activeTab: 'all' | 'unread' = 'all';

	onMount(async () => {
		await loadNotifications();
		loading = false;
	});

	$: displayedMessages = activeTab === 'unread'
		? $notifications.filter(n => !n.read)
		: $notifications;

	function formatDate(timestampMs: number): string {
		const date = new Date(timestampMs);
		const now = new Date();
		const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

		if (diffDays === 0) return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
		if (diffDays === 1) return 'Yesterday';
		if (diffDays < 7) return date.toLocaleDateString([], { weekday: 'long' });
		return date.toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' });
	}

	async function handleMarkAsRead(id: string, read: boolean) {
		await markAsRead(id, read);
	}
</script>

<svelte:head>
	<title>Messages</title>
</svelte:head>

<div class="mt-4 px-4 md:px-6">
	<div class="mb-6">
		<Heading tag="h2" class="text-2xl font-bold text-gray-900">Messages</Heading>
		<p class="mt-1 text-sm text-gray-500">Official correspondence with legal standing.</p>
	</div>

	<!-- Tabs -->
	<div class="flex gap-4 border-b border-gray-200 mb-4">
		<button
			class="pb-2 text-sm font-medium transition-colors {activeTab === 'all' ? 'border-b-2 border-gray-900 text-gray-900' : 'text-gray-500 hover:text-gray-700'}"
			on:click={() => activeTab = 'all'}
		>
			All ({$notifications.length})
		</button>
		<button
			class="pb-2 text-sm font-medium transition-colors {activeTab === 'unread' ? 'border-b-2 border-gray-900 text-gray-900' : 'text-gray-500 hover:text-gray-700'}"
			on:click={() => activeTab = 'unread'}
		>
			Unread ({$unreadCount})
		</button>
	</div>

	{#if loading}
		<div class="flex justify-center items-center py-16">
			<Spinner size="6" />
		</div>
	{:else if displayedMessages.length === 0}
		<div class="flex flex-col items-center justify-center py-16 text-gray-400">
			<IconInbox size={48} class="mb-4" />
			<p class="text-lg font-medium text-gray-500">
				{activeTab === 'unread' ? 'No unread messages' : 'No messages yet'}
			</p>
			<p class="text-sm text-gray-400 mt-1">
				{activeTab === 'unread' ? 'You\'re all caught up.' : 'Official correspondence will appear here.'}
			</p>
		</div>
	{:else}
		<div class="space-y-2">
			{#each displayedMessages as message (message.id)}
				<button
					class="w-full text-left p-4 rounded-lg border transition-colors {message.read ? 'border-gray-100 bg-white hover:bg-gray-50' : 'border-gray-200 bg-gray-50 hover:bg-gray-100'}"
					on:click={() => handleMarkAsRead(message.id, !message.read)}
				>
					<div class="flex items-start gap-3">
						<div class="flex-shrink-0 mt-0.5">
							{#if message.read}
								<IconMailOpened size={20} class="text-gray-400" />
							{:else}
								<IconMail size={20} class="text-gray-700" />
							{/if}
						</div>
						<div class="flex-1 min-w-0">
							<div class="flex items-center justify-between gap-2">
								<h4 class="text-sm truncate {message.read ? 'font-normal text-gray-600' : 'font-semibold text-gray-900'}">
									{message.title}
								</h4>
								<span class="flex-shrink-0 text-xs text-gray-400">
									{formatDate(message.timestamp_ms)}
								</span>
							</div>
							<p class="mt-1 text-sm text-gray-500 line-clamp-2">{message.message}</p>
						</div>
					</div>
				</button>
			{/each}
		</div>
	{/if}
</div>
