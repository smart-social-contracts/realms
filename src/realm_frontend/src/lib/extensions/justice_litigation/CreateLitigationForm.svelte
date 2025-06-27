<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { Card, Input, Textarea, Button, Alert } from 'flowbite-svelte';
	import { backend } from '$lib/canisters';
	
	export let userPrincipalId = '';
	
	const dispatch = createEventDispatcher();
	
	let defendantPrincipal = '';
	let caseTitle = '';
	let description = '';
	let creating = false;
	let error = '';
	let success = false;
	
	function resetForm() {
		defendantPrincipal = '';
		caseTitle = '';
		description = '';
		error = '';
		success = false;
	}
	
	async function createLitigation() {
		if (!defendantPrincipal.trim() || !caseTitle.trim() || !description.trim()) {
			error = 'All fields are required';
			return;
		}
		
		creating = true;
		error = '';
		success = false;
		
		try {
			const callParams = {
				requester_principal: userPrincipalId,
				defendant_principal: defendantPrincipal.trim(),
				case_title: caseTitle.trim(),
				description: description.trim()
			};
			
			console.log('Creating litigation with parameters:', callParams);
			
			const response = await backend.extension_sync_call({
				extension_name: "justice_litigation",
				function_name: "create_litigation",
				args: JSON.stringify(callParams)
			});
			
			console.log('Create litigation response:', response);
			
			if (response.success) {
				const data = JSON.parse(response.response);
				console.log('Parsed litigation creation data:', data);
				
				if (data.success) {
					success = true;
					setTimeout(() => {
						resetForm();
						dispatch('litigationCreated');
					}, 2000);
				} else {
					error = `Failed to create litigation: ${data.error}`;
				}
			} else {
				error = `Failed to create litigation: ${response.response}`;
			}
		} catch (err) {
			console.error('Error creating litigation:', err);
			error = `Error creating litigation: ${err.message || err}`;
		} finally {
			creating = false;
		}
	}
</script>

<Card class="w-full">
	<div class="space-y-4">
		<div>
			<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">
				Create New Litigation Case
			</h3>
			<p class="text-sm text-gray-600 dark:text-gray-400 mb-6">
				Submit a new litigation request to the external justice system. All fields are required.
			</p>
		</div>
		
		<div class="space-y-4">
			<div>
				<Input
					type="text"
					id="defendant-principal"
					placeholder="Enter defendant's principal ID"
					label="Defendant Principal ID"
					bind:value={defendantPrincipal}
					disabled={creating}
				/>
			</div>
			
			<div>
				<Input
					type="text"
					id="case-title"
					placeholder="Enter case title"
					label="Case Title"
					bind:value={caseTitle}
					disabled={creating}
				/>
			</div>
			
			<div>
				<label for="description" class="block mb-2 text-sm font-medium text-gray-900 dark:text-white">
					Case Description
				</label>
				<Textarea
					id="description"
					placeholder="Provide detailed description of the dispute..."
					rows="4"
					bind:value={description}
					disabled={creating}
				/>
			</div>
		</div>
		
		{#if error}
			<Alert color="red">
				<span class="font-medium">Error:</span> {error}
			</Alert>
		{/if}
		
		{#if success}
			<Alert color="green">
				<span class="font-medium">Success:</span> Litigation case created successfully!
			</Alert>
		{/if}
		
		<div class="flex justify-end gap-2">
			<Button color="alternative" on:click={resetForm} disabled={creating}>
				Reset Form
			</Button>
			<Button 
				color="primary" 
				on:click={createLitigation} 
				disabled={creating || !defendantPrincipal.trim() || !caseTitle.trim() || !description.trim()}
			>
				{#if creating}
					<div class="flex items-center">
						<span class="animate-spin inline-block w-4 h-4 border-2 border-t-transparent border-white rounded-full mr-2"></span>
						<span>Creating...</span>
					</div>
				{:else}
					Create Litigation
				{/if}
			</Button>
		</div>
	</div>
</Card>
