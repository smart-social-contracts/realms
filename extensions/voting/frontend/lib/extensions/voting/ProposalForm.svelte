<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { Card, Button, Input, Label, Textarea, Alert } from 'flowbite-svelte';
	import { CheckOutline, CloseOutline } from 'flowbite-svelte-icons';
	import { backend } from '$lib/canisters';
	import { principal } from '$lib/stores/auth';
	import { _ } from 'svelte-i18n';
	
	const dispatch = createEventDispatcher();
	
	let title = '';
	let description = '';
	let codeUrl = '';
	let submitting = false;
	let error = '';
	let success = '';
	
	async function handleSubmit() {
		if (!title.trim() || !description.trim() || !codeUrl.trim()) {
			error = $_('extensions.voting.form.validation.required_fields');
			return;
		}
		
		if (!isValidUrl(codeUrl)) {
			error = $_('extensions.voting.form.validation.invalid_url');
			return;
		}
		
		try {
			submitting = true;
			error = '';
			success = '';
			
			const response = await backend.extension_sync_call({
				extension_name: "voting",
				function_name: "submit_proposal",
				args: JSON.stringify({
					title: title.trim(),
					description: description.trim(),
					code_url: codeUrl.trim(),
					proposer: $principal || 'anonymous'
				})
			});
			
			console.log('Submit proposal response:', response);
			
			if (response.success) {
				const data = JSON.parse(response.response);
				if (data.success) {
					success = $_('extensions.voting.form.success');
					// Reset form
					title = '';
					description = '';
					codeUrl = '';
					// Notify parent component
					setTimeout(() => {
						dispatch('submitted', data.data);
					}, 1500);
				} else {
					error = data.error || $_('extensions.voting.form.error.submit_failed');
				}
			} else {
				error = $_('extensions.voting.form.error.backend_error');
			}
		} catch (e) {
			console.error('Error submitting proposal:', e);
			error = $_('extensions.voting.form.error.network_error');
		} finally {
			submitting = false;
		}
	}
	
	function handleCancel() {
		title = '';
		description = '';
		codeUrl = '';
		error = '';
		success = '';
		dispatch('cancelled');
	}
	
	function isValidUrl(string: string) {
		try {
			new URL(string);
			return true;
		} catch (_) {
			return false;
		}
	}
</script>

<Card>
	<div class="mb-6">
		<h2 class="text-xl font-semibold text-gray-900 mb-2">
			{$_('extensions.voting.form.title')}
		</h2>
		<p class="text-gray-600">
			{$_('extensions.voting.form.description')}
		</p>
	</div>

	{#if error}
		<Alert color="red" class="mb-4">
			<span class="font-medium">{$_('extensions.voting.error')}</span>
			{error}
		</Alert>
	{/if}

	{#if success}
		<Alert color="green" class="mb-4">
			<CheckOutline class="w-4 h-4 mr-2 inline" />
			<span class="font-medium">{success}</span>
		</Alert>
	{/if}

	<form on:submit|preventDefault={handleSubmit} class="space-y-4">
		<div>
			<Label for="proposal-title" class="mb-2">
				{$_('extensions.voting.form.fields.title')} *
			</Label>
			<Input
				id="proposal-title"
				bind:value={title}
				placeholder={$_('extensions.voting.form.placeholders.title')}
				required
				disabled={submitting}
			/>
		</div>

		<div>
			<Label for="proposal-description" class="mb-2">
				{$_('extensions.voting.form.fields.description')} *
			</Label>
			<Textarea
				id="proposal-description"
				bind:value={description}
				placeholder={$_('extensions.voting.form.placeholders.description')}
				rows="4"
				required
				disabled={submitting}
			/>
		</div>

		<div>
			<Label for="code-url" class="mb-2">
				{$_('extensions.voting.form.fields.code_url')} *
			</Label>
			<Input
				id="code-url"
				type="url"
				bind:value={codeUrl}
				placeholder={$_('extensions.voting.form.placeholders.code_url')}
				required
				disabled={submitting}
			/>
			<p class="text-sm text-gray-500 mt-1">
				{$_('extensions.voting.form.help.code_url')}
			</p>
		</div>

		<div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
			<h4 class="font-medium text-yellow-800 mb-2">
				{$_('extensions.voting.form.security.title')}
			</h4>
			<ul class="text-sm text-yellow-700 space-y-1">
				<li>• {$_('extensions.voting.form.security.point1')}</li>
				<li>• {$_('extensions.voting.form.security.point2')}</li>
				<li>• {$_('extensions.voting.form.security.point3')}</li>
			</ul>
		</div>

		<div class="flex justify-end space-x-3 pt-4">
			<Button 
				color="alternative"
				on:click={handleCancel}
				disabled={submitting}
			>
				<CloseOutline class="w-4 h-4 mr-2" />
				{$_('extensions.voting.form.buttons.cancel')}
			</Button>
			<Button 
				type="submit"
				disabled={submitting || !title.trim() || !description.trim() || !codeUrl.trim()}
			>
				{#if submitting}
					<div class="w-4 h-4 mr-2 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
					{$_('extensions.voting.form.buttons.submitting')}
				{:else}
					<CheckOutline class="w-4 h-4 mr-2" />
					{$_('extensions.voting.form.buttons.submit')}
				{/if}
			</Button>
		</div>
	</form>
</Card>
