<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { ToolbarButton, Badge } from 'flowbite-svelte';
    import { BellSolid } from 'flowbite-svelte-icons';
    import { unreadCount, loadNotifications } from '$lib/stores/notifications';

    onMount(() => {
        loadNotifications();
        // TODO: temporarily disabled
        // const interval = setInterval(loadNotifications, 30000);
        // return () => clearInterval(interval);
    });

    function handleClick() {
        goto('/extensions/notifications');
    }
</script>

<div class="relative mr-4">
    <ToolbarButton 
        size="lg" 
        class="-mx-0.5 hover:text-gray-900 dark:hover:text-white"
        on:click={handleClick}
    >
        <BellSolid size="lg" />
    </ToolbarButton>
    {#if $unreadCount > 0}
        <Badge 
            color="red" 
            rounded 
            class="absolute -top-1 -right-1 px-2 py-1 text-xs font-bold leading-none text-white bg-red-600 border-2 border-white dark:border-gray-800 shadow-lg"
        >
            {$unreadCount > 99 ? '99+' : $unreadCount}
        </Badge>
    {/if}
</div>
