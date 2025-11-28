<script lang="ts">
	import { Card, Button, Label, Input, Heading } from 'flowbite-svelte';
	import { _ } from 'svelte-i18n';

	let openChatHandle = '';
	let telegramHandle = '';

	function saveHandles() {
		// Placeholder for save logic
		console.log('Saving handles:', { openChat: openChatHandle, telegram: telegramHandle });
	}
</script>

<Card>
	<Heading tag="h3" class="mb-4 text-xl font-bold dark:text-white">
		{$_('settings.messaging_handles.title', { default: 'Messaging Handles' })}
	</Heading>
	<div class="grid grid-cols-1 gap-6">
			<div>
				<Label for="openchat" class="mb-2 flex items-center">
					<img src="/images/openchat.png" alt="OpenChat Logo" class="mr-2 h-6 w-6">
					OpenChat Handle
				</Label>
				<Input type="text" id="openchat" placeholder="@yourhandle" bind:value={openChatHandle} />
			</div>
			<div>
				<Label for="telegram" class="mb-2 flex items-center">
					<img src="/images/telegram.png" alt="Telegram Logo" class="mr-2 h-6 w-6">
					Telegram Handle
				</Label>
				<Input type="text" id="telegram" placeholder="@yourhandle" bind:value={telegramHandle} />
			</div>
		</div>
	<div class="mt-6">
		<Button on:click={saveHandles}>
			{$_('settings.messaging_handles.save_button', { default: 'Save' })}
		</Button>
	</div>
</Card>
