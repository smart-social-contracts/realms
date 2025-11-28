<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { Button, ButtonGroup } from 'flowbite-svelte';
	import { CheckOutline, CloseOutline, MinusOutline } from 'flowbite-svelte-icons';
	import { backend } from '$lib/canisters';
	import { principal } from '$lib/stores/auth';
	import { _ } from 'svelte-i18n';
	
	export let proposal;
	export let compact = false;
	
	const dispatch = createEventDispatcher();
	
	let voting = false;
	let error = '';
	
	async function castVote(vote: 'yes' | 'no' | 'abstain') {
		try {
			voting = true;
			error = '';
			
			const response = await backend.extension_sync_call({
				extension_name: "voting",
				function_name: "cast_vote",
				args: JSON.stringify({
					proposal_id: proposal.id,
					vote: vote,
					voter: $principal || 'anonymous'
				})
			});
			
			console.log('Vote response:', response);
			
			if (response.success) {
				const data = JSON.parse(response.response);
				if (data.success) {
					dispatch('vote', { proposal_id: proposal.id, vote });
				} else {
					error = data.error || 'Failed to cast vote';
				}
			} else {
				error = 'Failed to communicate with backend';
			}
		} catch (e) {
			console.error('Error casting vote:', e);
			error = 'Error casting vote: ' + e.message;
		} finally {
			voting = false;
		}
	}
</script>

{#if proposal.status === 'voting'}
	<div class="voting-card" class:compact>
		{#if !compact}
			<h4 class="text-sm font-medium text-gray-900 mb-3">
				{$_('extensions.voting.cast_vote')}
			</h4>
		{/if}
		
		{#if error}
			<div class="text-red-600 text-sm mb-2">{error}</div>
		{/if}
		
		<ButtonGroup class="w-full">
			<Button 
				color="green"
				size={compact ? "xs" : "sm"}
				disabled={voting}
				on:click={() => castVote('yes')}
				class="flex-1"
			>
				<CheckOutline class="w-3 h-3 mr-1" />
				{$_('extensions.voting.vote.yes')}
			</Button>
			<Button 
				color="red"
				size={compact ? "xs" : "sm"}
				disabled={voting}
				on:click={() => castVote('no')}
				class="flex-1"
			>
				<CloseOutline class="w-3 h-3 mr-1" />
				{$_('extensions.voting.vote.no')}
			</Button>
			<Button 
				color="alternative"
				size={compact ? "xs" : "sm"}
				disabled={voting}
				on:click={() => castVote('abstain')}
				class="flex-1"
			>
				<MinusOutline class="w-3 h-3 mr-1" />
				{$_('extensions.voting.vote.abstain')}
			</Button>
		</ButtonGroup>
		
		{#if voting}
			<div class="text-center text-sm text-gray-500 mt-2">
				{$_('extensions.voting.casting_vote')}
			</div>
		{/if}
	</div>
{:else}
	<div class="text-sm text-gray-500">
		{$_('extensions.voting.voting_not_active')}
	</div>
{/if}

<style>
	.voting-card.compact {
		font-size: 0.875rem;
	}
</style>
