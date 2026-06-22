<script lang="ts">
	import { Breadcrumb, BreadcrumbItem } from 'flowbite-svelte';
	import { page } from '$app/stores';
	import { sidebarConfig } from '$lib/stores/sidebar';
	import { resolveBreadcrumb } from '$lib/utils/breadcrumb';
	import { parseExtensionIdFromPath } from '$lib/utils/extension-manifest';
	import ExtensionInfoIcon from '$lib/components/ExtensionInfoIcon.svelte';

	$: segments = resolveBreadcrumb($page.url.pathname, $sidebarConfig);
	$: showBreadcrumb = segments.length > 0 && $page.url.pathname !== '/';
	$: extensionId = parseExtensionIdFromPath($page.url.pathname);
</script>

{#if showBreadcrumb}
	<div class="mb-6 flex items-center gap-1.5 px-4 pt-4 lg:px-0 lg:pt-4">
		<Breadcrumb class="mb-0">
			{#each segments as segment, index}
				<BreadcrumbItem href={index < segments.length - 1 ? segment.href : undefined}>
					{segment.label}
				</BreadcrumbItem>
			{/each}
		</Breadcrumb>
		{#if extensionId}
			<ExtensionInfoIcon {extensionId} />
		{/if}
	</div>
{/if}
