<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { Card, Label, Input, Textarea, Button, Alert, Spinner } from 'flowbite-svelte';
	import { backend } from '$lib/canisters';
	
	export let userPrincipal: string;
	
	const dispatch = createEventDispatcher();
	
	let formData = {
		title: '',
		description: '',
		author: '',
		forum_url: '',
		voting_deadline: ''
	};
	
	let loading = false;
	let error = '';
	let success = false;
	
	async function submitProposal() {
		try {
			loading = true;
			error = '';
			success = false;
			
			if (!formData.title.trim()) {
				error = 'Title is required';
				return;
			}
			
			if (!formData.description.trim()) {
				error = 'Description is required';
				return;
			}
			
			if (!formData.author.trim()) {
				error = 'Author is required';
				return;
			}
			
			const response = await backend.extension_sync_call({
				extension_name: "proposal_manager",
				function_name: "create_proposal",
				args: JSON.stringify({
					...formData,
					created_by: userPrincipal
				})
			});
			
			if (response.success) {
				const result = JSON.parse(response.response);
				if (result.success) {
					success = true;
					formData = {
						title: '',
						description: '',
						author: '',
						forum_url: '',
						voting_deadline: ''
					};
					dispatch('proposalCreated', { proposalId: result.proposal_id });
				} else {
					error = result.error || 'Failed to create proposal';
				}
			} else {
				error = response.response || 'Failed to call extension';
			}
		} catch (e) {
			console.error('Error creating proposal:', e);
			error = 'Failed to create proposal';
		} finally {
			loading = false;
		}
	}
	
	function resetForm() {
		formData = {
			title: '',
			description: '',
			author: '',
			forum_url: '',
			voting_deadline: ''
		};
		error = '';
		success = false;
	}
</script>

<div class="proposal-form">
	<Card class="w-full">
		<div class="space-y-4">
			<div>
				<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Submit New Proposal</h3>
				<p class="text-sm text-gray-600 dark:text-gray-400 mb-6">
					Create a new proposal for community consideration. All fields marked with * are required.
				</p>
			</div>
			
			{#if error}
				<Alert color="red">
					<span class="font-medium">Error:</span> {error}
				</Alert>
			{/if}
			
			{#if success}
				<Alert color="green">
					<span class="font-medium">Success:</span> Your proposal has been submitted successfully!
				</Alert>
			{/if}
			
			<div class="space-y-4">
				<div>
					<Label for="title" class="mb-2">Title *</Label>
					<Input
						id="title"
						bind:value={formData.title}
						placeholder="Enter proposal title"
						disabled={loading}
						required
					/>
				</div>
				
				<div>
					<Label for="description" class="mb-2">Description *</Label>
					<Textarea
						id="description"
						bind:value={formData.description}
						placeholder="Provide a detailed description of your proposal"
						rows="6"
						disabled={loading}
						required
					/>
				</div>
				
				<div>
					<Label for="author" class="mb-2">Author *</Label>
					<Input
						id="author"
						bind:value={formData.author}
						placeholder="Your name or organization"
						disabled={loading}
						required
					/>
				</div>
				
				<div>
					<Label for="forum_url" class="mb-2">Forum Discussion URL</Label>
					<Input
						id="forum_url"
						bind:value={formData.forum_url}
						placeholder="https://forum.example.com/discussion/123"
						disabled={loading}
						type="url"
					/>
					<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
						Optional: Link to forum discussion or additional resources
					</p>
				</div>
				
				<div>
					<Label for="voting_deadline" class="mb-2">Voting Deadline</Label>
					<Input
						id="voting_deadline"
						bind:value={formData.voting_deadline}
						disabled={loading}
						type="datetime-local"
					/>
					<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
						Optional: When voting should end (leave empty for admin to set)
					</p>
				</div>
			</div>
			
			<div class="flex gap-3 pt-4">
				<Button
					color="primary"
					disabled={loading || !formData.title.trim() || !formData.description.trim() || !formData.author.trim()}
					on:click={submitProposal}
				>
					{#if loading}
						<Spinner class="mr-2" size="4" />
						Submitting...
					{:else}
						Submit Proposal
					{/if}
				</Button>
				
				<Button color="alternative" disabled={loading} on:click={resetForm}>
					Reset Form
				</Button>
			</div>
			
			<div class="text-xs text-gray-500 dark:text-gray-400 pt-2 border-t">
				<p><strong>Note:</strong> Submitted proposals will be reviewed by administrators before being opened for voting.</p>
			</div>
		</div>
	</Card>
</div>
