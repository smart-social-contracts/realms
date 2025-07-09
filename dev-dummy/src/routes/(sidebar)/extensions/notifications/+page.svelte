<script>
	import { Card, Button, Badge } from 'flowbite-svelte';
	import { CheckOutline, EyeSolid, BellSolid } from 'flowbite-svelte-icons';
	import { mockNotifications } from '$lib/dummy-data/extensions';

	function formatDate(dateStr) {
		return new Date(dateStr).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function getNotificationIcon(type) {
		switch(type) {
			case 'warning':
				return '⚠️';
			case 'success':
				return '✅';
			case 'info':
				return 'ℹ️';
			case 'error':
				return '❌';
			default:
				return '📢';
		}
	}

	function getNotificationColor(type) {
		switch(type) {
			case 'warning':
				return 'yellow';
			case 'success':
				return 'green';
			case 'info':
				return 'blue';
			case 'error':
				return 'red';
			default:
				return 'gray';
		}
	}

	let notifications = mockNotifications;
	$: unreadCount = notifications.filter(n => !n.read).length;

	function markAsRead(notificationId) {
		notifications = notifications.map(n => 
			n.id === notificationId ? { ...n, read: true } : n
		);
	}

	function markAllAsRead() {
		notifications = notifications.map(n => ({ ...n, read: true }));
	}
</script>

<div class="py-6">
	<div class="mb-8">
		<div class="flex items-center justify-between">
			<div>
				<h1 class="text-2xl font-semibold text-gray-900 dark:text-gray-200">Notifications</h1>
				<p class="text-gray-600 dark:text-gray-400">
					{unreadCount} unread notification{unreadCount !== 1 ? 's' : ''}
				</p>
			</div>
			{#if unreadCount > 0}
				<Button size="sm" on:click={markAllAsRead}>
					<CheckOutline class="w-4 h-4 mr-2" />
					Mark All as Read
				</Button>
			{/if}
		</div>
	</div>

	<div class="space-y-4">
		{#each notifications as notification}
			<Card class="relative {!notification.read ? 'border-l-4 border-l-blue-500' : ''}">
				<div class="flex items-start justify-between">
					<div class="flex items-start space-x-3 flex-1">
						<div class="text-2xl">
							{getNotificationIcon(notification.type)}
						</div>
						<div class="flex-1">
							<div class="flex items-center space-x-2 mb-1">
								<h3 class="font-medium text-gray-900 dark:text-gray-200">
									{notification.title}
								</h3>
								{#if !notification.read}
									<span class="w-2 h-2 bg-blue-600 rounded-full"></span>
								{/if}
							</div>
							<p class="text-gray-600 dark:text-gray-400 mb-2">
								{notification.message}
							</p>
							<div class="flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400">
								<span>{formatDate(notification.timestamp)}</span>
								<Badge color={getNotificationColor(notification.type)}>
									{notification.type}
								</Badge>
							</div>
						</div>
					</div>
					<div class="flex items-center space-x-2">
						{#if notification.action_url}
							<Button size="xs" href={notification.action_url}>
								View Details
							</Button>
						{/if}
						{#if !notification.read}
							<Button size="xs" color="light" on:click={() => markAsRead(notification.id)}>
								<EyeSolid class="w-3 h-3" />
							</Button>
						{/if}
					</div>
				</div>
			</Card>
		{/each}

		{#if notifications.length === 0}
			<Card class="text-center py-8">
				<BellSolid class="w-12 h-12 mx-auto text-gray-400 mb-4" />
				<h3 class="text-lg font-medium text-gray-900 dark:text-gray-200 mb-2">No notifications</h3>
				<p class="text-gray-600 dark:text-gray-400">You're all caught up!</p>
			</Card>
		{/if}
	</div>
</div>
