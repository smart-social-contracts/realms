<script lang="ts">
	import { Avatar, Button, Card, Heading } from 'flowbite-svelte';
	import { UploadSolid } from 'flowbite-svelte-icons';

	export let src, title, description: string;
</script>

<Card
	size="xl"
	class="block shadow-sm sm:flex sm:space-x-4 sm:py-6 xl:block xl:space-x-0 2xl:flex 2xl:space-x-4"
	horizontal
>
<div class="flex items-center justify-center h-28 w-28 bg-gray-200 rounded-lg">
    <img src={src} alt={title} class="h-full w-full object-contain rounded-lg" />
</div>



	<div class="py-0.5">
		<Heading tag="h3" class="text-xl">{title}</Heading>
		<p class="mb-4 mt-1 pt-px text-sm">{description}</p>
		<div class="flex items-center space-x-4">
			<Button size="sm" class="px-3" color="alternative">Update</Button>
			<Button size="sm" class="px-3" color="alternative">Delete</Button>
		</div>
	</div>
</Card>

<!--
@component
[Go to docs](https://flowbite-svelte-admin-dashboard.vercel.app/)
## Props
@prop export let src: string;
-->
