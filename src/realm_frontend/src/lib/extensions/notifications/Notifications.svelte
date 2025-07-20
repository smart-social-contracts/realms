<script lang="ts">
    import { onMount } from 'svelte';
    import { Card, Button, Badge, Spinner } from 'flowbite-svelte';
    import { CheckOutline, EyeSolid } from 'flowbite-svelte-icons';
    import { notifications, unreadCount, loadNotifications, markAsRead, type NotificationItem } from '$lib/stores/notifications';
    import { getIcon } from '$lib/utils/iconMap';
    import { goto } from '$app/navigation';
    import { _ } from 'svelte-i18n';

    let loading = true;
    let selectedTab = 'all';

    onMount(async () => {
        await loadNotifications();
        loading = false;
    });

    $: filteredNotifications = $notifications.filter(notification => {
        if (selectedTab === 'unread') return !notification.read;
        return true;
    });

    async function handleMarkAsRead(notification: NotificationItem) {
        if (!notification.read) {
            await markAsRead(notification.id);
        }
        if (notification.href) {
            goto(notification.href);
        }
    }

    async function markAllAsRead() {
        const unreadNotifications = $notifications.filter(n => !n.read);
        for (const notification of unreadNotifications) {
            await markAsRead(notification.id);
        }
    }

    function getColorClass(color?: string) {
        switch (color) {
            case 'green': return 'text-green-600 bg-green-100 dark:bg-green-800 dark:text-green-200';
            case 'blue': return 'text-blue-600 bg-blue-100 dark:bg-blue-800 dark:text-blue-200';
            case 'purple': return 'text-purple-600 bg-purple-100 dark:bg-purple-800 dark:text-purple-200';
            case 'red': return 'text-red-600 bg-red-100 dark:bg-red-800 dark:text-red-200';
            default: return 'text-gray-600 bg-gray-100 dark:bg-gray-800 dark:text-gray-200';
        }
    }
</script>

<div class="p-6">
    <div class="flex justify-between items-center mb-6">
        <div>
            <h1 class="text-2xl font-bold text-gray-900 dark:text-white">{$_('extensions.notifications.title')}</h1>
            <p class="text-gray-600 dark:text-gray-400">
                {$_('extensions.notifications.unread_count', { values: { count: $unreadCount } })}
            </p>
        </div>
        {#if $unreadCount > 0}
            <Button color="alternative" on:click={markAllAsRead}>
                <CheckOutline class="w-4 h-4 mr-2" />
                {$_('extensions.notifications.mark_all_read')}
            </Button>
        {/if}
    </div>

    <div class="flex space-x-4 mb-6">
        <Button 
            color={selectedTab === 'all' ? 'primary' : 'alternative'}
            on:click={() => selectedTab = 'all'}
        >
            {$_('extensions.notifications.tabs.all', { values: { count: $notifications.length } })}
        </Button>
        <Button 
            color={selectedTab === 'unread' ? 'primary' : 'alternative'}
            on:click={() => selectedTab = 'unread'}
        >
            {$_('extensions.notifications.tabs.unread', { values: { count: $unreadCount } })}
        </Button>
    </div>

    {#if loading}
        <div class="flex justify-center items-center py-12">
            <Spinner size="8" />
        </div>
    {:else if filteredNotifications.length === 0}
        <Card class="text-center py-12">
            <EyeSolid class="w-12 h-12 mx-auto mb-4 text-gray-400" />
            <h3 class="text-lg font-medium text-gray-900 dark:text-white mb-2">
                {selectedTab === 'unread' ? $_('extensions.notifications.empty_states.no_unread') : $_('extensions.notifications.empty_states.no_notifications')}
            </h3>
            <p class="text-gray-600 dark:text-gray-400">
                {selectedTab === 'unread' 
                    ? $_('extensions.notifications.empty_states.all_caught_up') 
                    : $_('extensions.notifications.empty_states.none_available')}
            </p>
        </Card>
    {:else}
        <div class="space-y-2">
            {#each filteredNotifications as notification (notification.id)}
                <Card 
                    class="cursor-pointer transition-colors hover:bg-gray-50 dark:hover:bg-gray-800 {!notification.read ? 'border-l-4 border-l-blue-500' : ''}"
                    on:click={() => handleMarkAsRead(notification)}
                >
                    <div class="flex items-start space-x-4">
                        <div class="flex-shrink-0">
                            <div class="w-10 h-10 rounded-full flex items-center justify-center {getColorClass(notification.color)}">
                                <svelte:component 
                                    this={getIcon(notification.icon || 'bell')} 
                                    class="w-5 h-5" 
                                />
                            </div>
                        </div>
                        <div class="flex-1 min-w-0">
                            <div class="flex items-center justify-between">
                                <h4 class="text-sm font-medium text-gray-900 dark:text-white truncate">
                                    {notification.title}
                                </h4>
                                <div class="flex items-center space-x-2">
                                    {#if !notification.read}
                                        <Badge color="blue" class="text-xs">{$_('extensions.notifications.badge_new')}</Badge>
                                    {/if}
                                    <span class="text-xs text-gray-500 dark:text-gray-400">
                                        {notification.timestamp}
                                    </span>
                                </div>
                            </div>
                            <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
                                {notification.message}
                            </p>
                        </div>
                    </div>
                </Card>
            {/each}
        </div>
    {/if}
</div>
