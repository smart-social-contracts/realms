<script lang="ts">
    import { onMount } from 'svelte';
    import Notifications from '$lib/extensions/notifications';
    import { SITE_NAME } from '$lib/globals';
    import MetaTag from '../../../utils/MetaTag.svelte';
    
    const path: string = '/extensions/notifications';
    const description: string = 'View and manage your notifications';
    const title: string = SITE_NAME + ' - Notifications';
    const subtitle: string = 'Notifications';
</script>

<svelte:head>
    <title>{title}</title>
    <MetaTag {title} {description} {path} />
</svelte:head>

<Notifications />
