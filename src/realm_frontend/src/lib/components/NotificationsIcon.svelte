<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { ToolbarButton, Badge } from 'flowbite-svelte';
    import { BellSolid } from 'flowbite-svelte-icons';
    import { unreadCount, loadNotifications } from '$lib/stores/notifications';

    onMount(() => {
        loadNotifications();
        const interval = setInterval(loadNotifications, 30000);
        return () => clearInterval(interval);
    });

    function handleClick() {
        goto('/extensions/notifications');
    }
</script>

<div class="relative mr-3">
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
            class="absolute -top-2 -right-2 z-10 min-w-[1rem] h-4 flex items-center justify-center text-xs font-medium bg-red-500 text-white border border-white dark:border-gray-800"
        >
            {$unreadCount > 99 ? '99+' : $unreadCount}
        </Badge>
    {/if}
</div>
