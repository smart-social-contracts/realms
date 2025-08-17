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

<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
	<!-- Left Column: Form -->
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
					rows="6"
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

	<!-- Right Column: Preview -->
	<Card class="bg-gray-50">
		<div class="mb-4">
			<h3 class="text-lg font-semibold text-gray-800 mb-2">
				{$_('extensions.voting.form.preview.title')}
			</h3>
			<p class="text-sm text-gray-600">
				{$_('extensions.voting.form.preview.description')}
			</p>
		</div>

		<div class="space-y-4">
			<!-- Title Preview -->
			<div>
				<h4 class="text-sm font-medium text-gray-700 mb-1">
					{$_('extensions.voting.form.fields.title')}
				</h4>
				<div class="bg-white border rounded-lg p-3 min-h-[2.5rem] flex items-center">
					{#if title.trim()}
						<span class="text-gray-900 font-medium">{title}</span>
					{:else}
						<span class="text-gray-400 italic">{$_('extensions.voting.form.preview.empty_title')}</span>
					{/if}
				</div>
			</div>

			<!-- Description Preview -->
			<div>
				<h4 class="text-sm font-medium text-gray-700 mb-1">
					{$_('extensions.voting.form.fields.description')}
				</h4>
				<div class="bg-white border rounded-lg p-3 min-h-[6rem]">
					{#if description.trim()}
						<p class="text-gray-700 whitespace-pre-wrap text-sm leading-relaxed">{description}</p>
					{:else}
						<span class="text-gray-400 italic text-sm">{$_('extensions.voting.form.preview.empty_description')}</span>
					{/if}
				</div>
			</div>

			<!-- Code URL Preview -->
			<div>
				<h4 class="text-sm font-medium text-gray-700 mb-1">
					{$_('extensions.voting.form.fields.code_url')}
				</h4>
				<div class="bg-white border rounded-lg p-3 min-h-[2.5rem] flex items-center">
					{#if codeUrl.trim()}
						<a 
							href={codeUrl} 
							target="_blank" 
							rel="noopener noreferrer"
							class="text-blue-600 hover:underline text-sm break-all"
						>
							{codeUrl}
						</a>
					{:else}
						<span class="text-gray-400 italic text-sm">{$_('extensions.voting.form.preview.empty_code_url')}</span>
					{/if}
				</div>
			</div>

			<!-- Proposal Summary -->
			{#if title.trim() && description.trim() && codeUrl.trim()}
				<div class="mt-6 pt-4 border-t border-gray-200">
					<h4 class="text-sm font-medium text-gray-700 mb-2">
						{$_('extensions.voting.form.preview.summary')}
					</h4>
					<div class="bg-blue-50 border border-blue-200 rounded-lg p-3">
						<div class="flex items-center gap-2 mb-2">
							<div class="w-2 h-2 bg-blue-500 rounded-full"></div>
							<span class="text-sm font-medium text-blue-800">
								{$_('extensions.voting.form.preview.ready_to_submit')}
							</span>
						</div>
						<ul class="text-xs text-blue-700 space-y-1">
							<li>✓ {$_('extensions.voting.form.preview.check_title')}</li>
							<li>✓ {$_('extensions.voting.form.preview.check_description')}</li>
							<li>✓ {$_('extensions.voting.form.preview.check_code_url')}</li>
						</ul>
					</div>
				</div>
			{:else}
				<div class="mt-6 pt-4 border-t border-gray-200">
					<h4 class="text-sm font-medium text-gray-700 mb-2">
						{$_('extensions.voting.form.preview.checklist')}
					</h4>
					<div class="space-y-2">
						<div class="flex items-center gap-2">
							<div class="w-4 h-4 rounded border-2 {title.trim() ? 'bg-green-500 border-green-500' : 'border-gray-300'}">
								{#if title.trim()}
									<CheckOutline class="w-3 h-3 text-white" />
								{/if}
							</div>
							<span class="text-sm {title.trim() ? 'text-green-700' : 'text-gray-500'}">
								{$_('extensions.voting.form.preview.check_title')}
							</span>
						</div>
						<div class="flex items-center gap-2">
							<div class="w-4 h-4 rounded border-2 {description.trim() ? 'bg-green-500 border-green-500' : 'border-gray-300'}">
								{#if description.trim()}
									<CheckOutline class="w-3 h-3 text-white" />
								{/if}
							</div>
							<span class="text-sm {description.trim() ? 'text-green-700' : 'text-gray-500'}">
								{$_('extensions.voting.form.preview.check_description')}
							</span>
						</div>
						<div class="flex items-center gap-2">
							<div class="w-4 h-4 rounded border-2 {codeUrl.trim() ? 'bg-green-500 border-green-500' : 'border-gray-300'}">
								{#if codeUrl.trim()}
									<CheckOutline class="w-3 h-3 text-white" />
								{/if}
							</div>
							<span class="text-sm {codeUrl.trim() ? 'text-green-700' : 'text-gray-500'}">
								{$_('extensions.voting.form.preview.check_code_url')}
							</span>
						</div>
					</div>
				</div>
			{/if}
		</div>
	</Card>
</div>
