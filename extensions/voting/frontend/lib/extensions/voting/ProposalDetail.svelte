<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { Card, Button, Badge, Alert } from 'flowbite-svelte';
	import { LinkOutline, CalendarMonthOutline, UserCircleSolid, CodeBranchOutline } from 'flowbite-svelte-icons';
	import { _ } from 'svelte-i18n';
	import VotingCard from './VotingCard.svelte';
	
	export let proposal;
	
	const dispatch = createEventDispatcher();
	
	function getStatusColor(status: string) {
		switch (status) {
			case 'pending_review': return 'yellow';
			case 'pending_vote': return 'blue';
			case 'voting': return 'green';
			case 'accepted': return 'green';
			case 'rejected': return 'red';
			default: return 'gray';
		}
	}
	
	function formatDate(dateString: string) {
		if (!dateString) return 'N/A';
		return new Date(dateString).toLocaleString();
	}
	
	function handleVote(event) {
		dispatch('vote', event.detail);
	}
	
	function handleClose() {
		dispatch('close');
	}
</script>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-6 h-full">
			<!-- Left Column: Proposal Details -->
			<div class="space-y-6 overflow-y-auto max-h-[70vh]">
				<!-- Proposal Header -->
				<div>
					<div class="flex items-center gap-3 mb-3">
						<h2 class="text-2xl font-bold text-gray-900">
							{proposal.title}
						</h2>
						<Badge color={getStatusColor(proposal.status)} size="lg">
							{$_(`extensions.voting.status.${proposal.status}`)}
						</Badge>
					</div>
					
					<div class="flex items-center gap-4 text-sm text-gray-600">
						<div class="flex items-center gap-1">
							<UserCircleSolid class="w-4 h-4" />
							<span>{$_('extensions.voting.detail.proposer')}: {proposal.proposer}</span>
						</div>
						<div class="flex items-center gap-1">
							<CalendarMonthOutline class="w-4 h-4" />
							<span>{$_('extensions.voting.detail.created')}: {formatDate(proposal.created_at)}</span>
						</div>
					</div>
					
					{#if proposal.voting_deadline}
						<div class="flex items-center gap-1 text-sm text-gray-600 mt-1">
							<CalendarMonthOutline class="w-4 h-4" />
							<span>{$_('extensions.voting.detail.deadline')}: {formatDate(proposal.voting_deadline)}</span>
						</div>
					{/if}
					{#if proposal.code_url}
						<div class="flex items-center gap-1 text-sm">
							<LinkOutline class="w-4 h-4" />
							<a href={proposal.code_url} target="_blank" class="text-blue-600 hover:underline">
								{$_('extensions.voting.detail.view_code')}
							</a>
						</div>
					{/if}
				</div>

				<!-- Description -->
				<Card>
					<h3 class="text-lg font-semibold mb-3">{$_('extensions.voting.detail.description')}</h3>
					<p class="text-gray-700 whitespace-pre-wrap">{proposal.description}</p>
				</Card>

				<!-- Code Information -->
				<Card>
					<h3 class="text-lg font-semibold mb-3 flex items-center gap-2">
						<CodeBranchOutline class="w-5 h-5" />
						{$_('extensions.voting.detail.code_info')}
					</h3>
					
					<div class="space-y-3">
						<div>
							<div class="block text-sm font-medium text-gray-700 mb-1">
								{$_('extensions.voting.detail.code_url')}
							</div>
							<div class="flex items-center gap-2">
								<code class="bg-gray-100 px-2 py-1 rounded text-sm flex-1 break-all">
									{proposal.code_url}
								</code>
								<Button 
									size="xs" 
									color="light"
									href={proposal.code_url}
									target="_blank"
									rel="noopener noreferrer"
								>
									<LinkOutline class="w-3 h-3 mr-1" />
									{$_('extensions.voting.detail.view_code')}
								</Button>
							</div>
						</div>
						
						<div>
							<div class="block text-sm font-medium text-gray-700 mb-1">
								{$_('extensions.voting.detail.checksum')}
							</div>
							<code class="bg-gray-100 px-2 py-1 rounded text-sm block break-all">
								{proposal.code_checksum}
							</code>
						</div>
					</div>
				</Card>

				<!-- Voting Information -->
				{#if proposal.status === 'voting' || proposal.total_voters > 0}
					<Card>
						<h3 class="text-lg font-semibold mb-3">{$_('extensions.voting.detail.voting_info')}</h3>
						
						<div class="grid grid-cols-2 gap-4 mb-4">
							<div class="text-center">
								<div class="text-2xl font-bold text-green-600">{proposal.votes.yes}</div>
								<div class="text-sm text-gray-600">{$_('extensions.voting.votes.yes')}</div>
							</div>
							<div class="text-center">
								<div class="text-2xl font-bold text-red-600">{proposal.votes.no}</div>
								<div class="text-sm text-gray-600">{$_('extensions.voting.votes.no')}</div>
							</div>
							<div class="text-center">
								<div class="text-2xl font-bold text-gray-600">{proposal.votes.abstain}</div>
								<div class="text-sm text-gray-600">{$_('extensions.voting.votes.abstain')}</div>
							</div>
							<div class="text-center">
								<div class="text-2xl font-bold text-blue-600">{proposal.total_voters}</div>
								<div class="text-sm text-gray-600">{$_('extensions.voting.total_votes')}</div>
							</div>
						</div>
						
						{#if proposal.total_voters > 0}
							<div class="mb-4">
								<div class="flex justify-between text-sm text-gray-600 mb-1">
									<span>{$_('extensions.voting.approval_progress')}</span>
									<span>{((proposal.votes.yes / proposal.total_voters) * 100).toFixed(1)}%</span>
								</div>
								<div class="w-full bg-gray-200 rounded-full h-3">
									<div 
										class="bg-green-600 h-3 rounded-full transition-all duration-300" 
										style="width: {(proposal.votes.yes / proposal.total_voters) * 100}%"
									></div>
								</div>
								<div class="text-xs text-gray-500 mt-1">
									{$_('extensions.voting.threshold_required')}: {(proposal.required_threshold * 100).toFixed(0)}%
								</div>
							</div>
						{/if}
						
						{#if proposal.status === 'voting'}
							<VotingCard 
								{proposal}
								on:vote={handleVote}
							/>
						{/if}
					</Card>
				{/if}

				<!-- Security Warning -->
				<Alert color="yellow">
					<span class="font-medium">{$_('extensions.voting.detail.security_warning.title')}</span>
					{$_('extensions.voting.detail.security_warning.message')}
				</Alert>
			</div>

			<!-- Right Column: Code Diff Viewer -->
			<div class="bg-gray-50 rounded-lg border overflow-hidden">
				<div class="bg-gray-100 px-4 py-2 border-b flex items-center gap-2">
					<CodeBranchOutline class="w-4 h-4 text-gray-600" />
					<h3 class="font-semibold text-gray-800">{$_('extensions.voting.detail.code_diff')}</h3>
				</div>
				
				<div class="p-4 h-full max-h-[70vh] overflow-y-auto">
					<div class="font-mono text-sm space-y-1">
						<!-- Mock code diff display -->
						<div class="text-gray-500 mb-3">
							<span class="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">
								{proposal.code_url ? proposal.code_url.split('/').pop() : 'proposal.py'}
							</span>
						</div>
						
						<!-- Sample diff content -->
						<div class="bg-red-50 border-l-4 border-red-400 pl-3 py-1">
							<span class="text-red-600">- def calculate_fee(amount):</span>
						</div>
						<div class="bg-red-50 border-l-4 border-red-400 pl-3 py-1">
							<span class="text-red-600">-     return amount * 0.001  # 0.1% fee</span>
						</div>
						<div class="bg-green-50 border-l-4 border-green-400 pl-3 py-1">
							<span class="text-green-600">+ def calculate_fee(amount):</span>
						</div>
						<div class="bg-green-50 border-l-4 border-green-400 pl-3 py-1">
							<span class="text-green-600">+     return amount * 0.0011  # 0.11% fee (increased by 0.01%)</span>
						</div>
						<div class="pl-3 py-1">
							<span class="text-gray-700"></span>
						</div>
						<div class="pl-3 py-1">
							<span class="text-gray-700">class TransactionProcessor:</span>
						</div>
						<div class="pl-3 py-1">
							<span class="text-gray-700">    def __init__(self, realm_id):</span>
						</div>
						<div class="pl-3 py-1">
							<span class="text-gray-700">        self.realm_id = realm_id</span>
						</div>
						<div class="bg-green-50 border-l-4 border-green-400 pl-3 py-1">
							<span class="text-green-600">+         self.fee_rate = 0.0011  # Updated fee rate</span>
						</div>
						<div class="pl-3 py-1">
							<span class="text-gray-700"></span>
						</div>
						<div class="pl-3 py-1">
							<span class="text-gray-700">    def process_transaction(self, transaction):</span>
						</div>
						<div class="pl-3 py-1">
							<span class="text-gray-700">        amount = transaction.amount</span>
						</div>
						<div class="bg-red-50 border-l-4 border-red-400 pl-3 py-1">
							<span class="text-red-600">-         fee = calculate_fee(amount)</span>
						</div>
						<div class="bg-green-50 border-l-4 border-green-400 pl-3 py-1">
							<span class="text-green-600">+         fee = amount * self.fee_rate</span>
						</div>
						<div class="pl-3 py-1">
							<span class="text-gray-700">        net_amount = amount - fee</span>
						</div>
						<div class="pl-3 py-1">
							<span class="text-gray-700">        </span>
						</div>
						<div class="pl-3 py-1">
							<span class="text-gray-700">        # Log the transaction</span>
						</div>
						<div class="bg-green-50 border-l-4 border-green-400 pl-3 py-1">
							<span class="text-green-600">+         logger.info(f"Processing transaction: &#123;amount&#125;, fee: &#123;fee&#125;")</span>
						</div>
						<div class="pl-3 py-1">
							<span class="text-gray-700">        </span>
						</div>
						<div class="pl-3 py-1">
							<span class="text-gray-700">        return &#123;</span>
						</div>
						<div class="pl-3 py-1">
							<span class="text-gray-700">            'original_amount': amount,</span>
						</div>
						<div class="pl-3 py-1">
							<span class="text-gray-700">            'fee': fee,</span>
						</div>
						<div class="pl-3 py-1">
							<span class="text-gray-700">            'net_amount': net_amount</span>
						</div>
						<div class="pl-3 py-1">
							<span class="text-gray-700">        &#125;</span>
						</div>
						
						<!-- Diff stats -->
						<div class="mt-4 pt-3 border-t border-gray-200">
							<div class="text-xs text-gray-500 space-y-1">
								<div class="flex justify-between">
									<span>Lines added:</span>
									<span class="text-green-600 font-medium">+4</span>
								</div>
								<div class="flex justify-between">
									<span>Lines removed:</span>
									<span class="text-red-600 font-medium">-2</span>
								</div>
								<div class="flex justify-between">
									<span>Net change:</span>
									<span class="font-medium">+2 lines</span>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
</div>
