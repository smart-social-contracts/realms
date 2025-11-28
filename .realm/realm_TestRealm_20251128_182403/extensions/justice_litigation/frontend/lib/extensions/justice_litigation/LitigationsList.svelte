<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { Table, TableHead, TableHeadCell, TableBody, TableBodyRow, TableBodyCell, Badge, Button, Modal, Input, Textarea, Alert } from 'flowbite-svelte';
	import { ExclamationCircleSolid, CheckCircleSolid, ClockSolid } from 'flowbite-svelte-icons';
	import { backend } from '$lib/canisters';
	
	export let litigations = [];
	export let userProfile = 'member';
	export let userPrincipalId = '';
	
	const dispatch = createEventDispatcher();
	
	let showVerdictModal = false;
	let selectedLitigation = null;
	let verdictCode = '';
	let executingVerdict = false;
	let verdictError = '';
	let verdictSuccess = false;
	
	function getStatusColor(status) {
		switch (status) {
			case 'pending': return 'yellow';
			case 'in_review': return 'blue';
			case 'resolved': return 'green';
			default: return 'gray';
		}
	}
	
	function getStatusIcon(status) {
		switch (status) {
			case 'pending': return ClockSolid;
			case 'in_review': return ExclamationCircleSolid;
			case 'resolved': return CheckCircleSolid;
			default: return ClockSolid;
		}
	}
	
	function formatDate(dateString) {
		return new Date(dateString).toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}
	
	function truncatePrincipal(principal) {
		if (!principal) return 'Unknown';
		return principal.length > 12 ? `${principal.slice(0, 8)}...${principal.slice(-4)}` : principal;
	}
	
	function openVerdictModal(litigation) {
		selectedLitigation = litigation;
		verdictCode = `transfer("${litigation.defendant_principal}", "${litigation.requester_principal}", 1000, "Compensation for ${litigation.case_title}")`;
		showVerdictModal = true;
		verdictError = '';
		verdictSuccess = false;
	}
	
	function closeVerdictModal() {
		showVerdictModal = false;
		selectedLitigation = null;
		verdictCode = '';
		verdictError = '';
		verdictSuccess = false;
	}
	
	async function executeVerdict() {
		if (!selectedLitigation || !verdictCode.trim()) {
			verdictError = 'Verdict code is required';
			return;
		}
		
		executingVerdict = true;
		verdictError = '';
		verdictSuccess = false;
		
		try {
			const callParams = {
				litigation_id: selectedLitigation.id,
				verdict_code: verdictCode.trim(),
				executor_principal: userPrincipalId
			};
			
			console.log('Executing verdict with parameters:', callParams);
			
			const response = await backend.extension_sync_call({
				extension_name: "justice_litigation",
				function_name: "execute_verdict",
				args: JSON.stringify(callParams)
			});
			
			console.log('Execute verdict response:', response);
			
			if (response.success) {
				const data = JSON.parse(response.response);
				console.log('Parsed verdict execution data:', data);
				
				if (data.success) {
					verdictSuccess = true;
					setTimeout(() => {
						closeVerdictModal();
						dispatch('verdictExecuted');
					}, 2000);
				} else {
					verdictError = `Failed to execute verdict: ${data.error}`;
				}
			} else {
				verdictError = `Failed to execute verdict: ${response.response}`;
			}
		} catch (err) {
			console.error('Error executing verdict:', err);
			verdictError = `Error executing verdict: ${err.message || err}`;
		} finally {
			executingVerdict = false;
		}
	}
</script>

<div class="space-y-4">
	{#if litigations.length === 0}
		<div class="text-center py-8">
			<p class="text-gray-500 dark:text-gray-400">
				{userProfile === 'admin' ? 'No litigations found in the system.' : 'You have no litigation cases.'}
			</p>
		</div>
	{:else}
		<Table hoverable={true}>
			<TableHead>
				<TableHeadCell>Case ID</TableHeadCell>
				<TableHeadCell>Title</TableHeadCell>
				<TableHeadCell>Status</TableHeadCell>
				<TableHeadCell>Requester</TableHeadCell>
				{#if userProfile === 'admin'}
					<TableHeadCell>Defendant</TableHeadCell>
				{/if}
				<TableHeadCell>Date</TableHeadCell>
				{#if userProfile === 'admin'}
					<TableHeadCell>Actions</TableHeadCell>
				{/if}
			</TableHead>
			<TableBody>
				{#each litigations as litigation}
					<TableBodyRow>
						<TableBodyCell class="font-mono text-sm">{litigation.id}</TableBodyCell>
						<TableBodyCell>
							<div>
								<div class="font-medium">{litigation.case_title}</div>
								<div class="text-sm text-gray-500 dark:text-gray-400 truncate max-w-xs">
									{litigation.description}
								</div>
							</div>
						</TableBodyCell>
						<TableBodyCell>
							<Badge color={getStatusColor(litigation.status)} class="flex items-center gap-1 w-fit">
								<svelte:component this={getStatusIcon(litigation.status)} class="w-3 h-3" />
								{litigation.status.replace('_', ' ')}
							</Badge>
						</TableBodyCell>
						<TableBodyCell class="font-mono text-sm">
							{truncatePrincipal(litigation.requester_principal)}
						</TableBodyCell>
						{#if userProfile === 'admin'}
							<TableBodyCell class="font-mono text-sm">
								{truncatePrincipal(litigation.defendant_principal)}
							</TableBodyCell>
						{/if}
						<TableBodyCell class="text-sm">
							{formatDate(litigation.requested_at)}
						</TableBodyCell>
						{#if userProfile === 'admin'}
							<TableBodyCell>
								{#if litigation.status !== 'resolved'}
									<Button 
										size="xs" 
										color="primary" 
										on:click={() => openVerdictModal(litigation)}
									>
										Execute Verdict
									</Button>
								{:else}
									<span class="text-sm text-gray-500 dark:text-gray-400">Resolved</span>
								{/if}
							</TableBodyCell>
						{/if}
					</TableBodyRow>
				{/each}
			</TableBody>
		</Table>
	{/if}
</div>

<Modal bind:open={showVerdictModal} size="lg" autoclose={false} class="w-full">
	<div class="flex items-center gap-2 mb-4">
		<ExclamationCircleSolid class="w-6 h-6 text-primary-600" />
		<h3 class="text-xl font-semibold text-gray-900 dark:text-white">
			Execute Verdict
		</h3>
	</div>
	
	{#if selectedLitigation}
		<div class="space-y-4">
			<div class="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
				<h4 class="font-medium mb-2">Case Details</h4>
				<div class="space-y-1 text-sm">
					<div><span class="font-medium">ID:</span> {selectedLitigation.id}</div>
					<div><span class="font-medium">Title:</span> {selectedLitigation.case_title}</div>
					<div><span class="font-medium">Description:</span> {selectedLitigation.description}</div>
				</div>
			</div>
			
			<div>
				<label for="verdict-code" class="block mb-2 text-sm font-medium text-gray-900 dark:text-white">
					Verdict Code (Python/Codex)
				</label>
				<Textarea
					id="verdict-code"
					placeholder="Enter Python code for the verdict execution..."
					rows="4"
					bind:value={verdictCode}
					disabled={executingVerdict}
				/>
				<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
					Example: transfer("from_principal", "to_principal", amount, "memo")
				</p>
			</div>
			
			{#if verdictError}
				<Alert color="red">
					<span class="font-medium">Error:</span> {verdictError}
				</Alert>
			{/if}
			
			{#if verdictSuccess}
				<Alert color="green">
					<span class="font-medium">Success:</span> Verdict executed successfully!
				</Alert>
			{/if}
			
			<div class="flex justify-end gap-2">
				<Button color="alternative" on:click={closeVerdictModal} disabled={executingVerdict}>
					Cancel
				</Button>
				<Button color="primary" on:click={executeVerdict} disabled={executingVerdict || !verdictCode.trim()}>
					{#if executingVerdict}
						<div class="flex items-center">
							<span class="animate-spin inline-block w-4 h-4 border-2 border-t-transparent border-white rounded-full mr-2"></span>
							<span>Executing...</span>
						</div>
					{:else}
						Execute Verdict
					{/if}
				</Button>
			</div>
		</div>
	{/if}
</Modal>
