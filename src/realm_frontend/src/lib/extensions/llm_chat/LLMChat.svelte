<script lang="ts">
	import { onMount, afterUpdate } from 'svelte';
	import { Card, Button, Textarea, Spinner, Toggle } from 'flowbite-svelte';
	import { PaperPlaneSolid, MessagesSolid, DatabaseSolid } from 'flowbite-svelte-icons';
	import SvelteMarkdown from 'svelte-markdown';
	// @ts-ignore
	import { backend } from '$lib/canisters';

	// Define message interface to fix TypeScript errors
	interface ChatMessage {
		text: string;
		isUser: boolean;
	}

	// Interface for the payload sent to the LLM API
	interface LLMPayload {
		message: string;
		max_tokens: number;
		realm_data?: any;
	}

	 
	// State variables
	let messages: ChatMessage[] = [];
	let newMessage = '';
	let isLoading = false;
	let error = '';
	let messagesContainer: HTMLElement;
	let includeRealmData = true;
	let realmData: any = null;
	let isLoadingRealmData = false;

	// LLM API configuration
	// const API_URL = "https://jvql982sbyh2vo-5000.proxy.runpod.net/api/ask"; // Change this to your LLM API endpoint
	const API_URL = "http://localhost:5000/api/ask"; // Change this to your LLM API endpoint
	const REALM_CANISTER_ID = "uxrrr-q7777-77774-qaaaq-cai";

	// Auto-scroll to bottom of messages when content changes
	afterUpdate(() => {
		scrollToBottom();
	});

	// Watch for message changes to trigger scroll
	$: {
		messages;
		setTimeout(scrollToBottom, 100); // Delay slightly to ensure rendering is complete
	}

	// Function to scroll to bottom of messages container
	function scrollToBottom() {
		if (messagesContainer) {
			messagesContainer.scrollTop = messagesContainer.scrollHeight;
		}
	}

	// Function to fetch realm data
	async function fetchRealmData(): Promise<void> {
		if (isLoadingRealmData) return;
		
		isLoadingRealmData = true;
		try {
			// Call the backend extension to get realm data
			const response = await backend.extension_async_call({
				extension_name: "llm_chat",
				function_name: "get_realm_data",
				args: ""
			});
			
			realmData = response;
			console.log("Realm data fetched:", realmData);
		} catch (err) {
			console.error("Error fetching realm data:", err);
			error = "Failed to get realm data. LLM responses may be less accurate.";
		} finally {
			isLoadingRealmData = false;
		}
	}

	// Function to send a message to the LLM
	async function sendMessage(): Promise<void> {
		if (!newMessage.trim()) return;
		
		// Add user message to the chat
		messages = [...messages, { text: newMessage, isUser: true }];
		
		// Clear input and show loading state
		const messageToSend = newMessage;
		newMessage = '';
		isLoading = true;
		error = '';
		
		// // If realm data is enabled but not loaded, load it first
		// if (includeRealmData && !realmData) {
		// 	await fetchRealmData();
		// }
		
		try {
			// Prepare request payload
			const payload = {
				question: messageToSend,
				realm_canister_id: REALM_CANISTER_ID
			};
			
			// Make direct HTTP request to the LLM API
			const response = await fetch(API_URL, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'Accept': 'application/json'
				},
				body: JSON.stringify(payload)
			});

			if (!response.ok) {
				throw new Error(`HTTP error! Status: ${response.status}`);
			}

			const data = await response.json();
			
			// Add response to the chat
			messages = [...messages, { 
				text: data.ai_response || "No response from LLM", 
				isUser: false 
			}];
		} catch (err) {
			console.error("Error calling LLM:", err);
			error = "Failed to get response from LLM. Please try again.";
		} finally {
			isLoading = false;
		}
	}

	// Handle Enter key in textarea
	function handleKeydown(event: KeyboardEvent): void {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			sendMessage();
		}
	}
</script>

<div class="w-full h-full flex flex-col p-0 m-0 max-w-none">
	<h2 class="text-2xl font-bold p-4">LLM Chat</h2>
	
	<div class="w-full flex-grow flex flex-col overflow-hidden">
		<Card class="w-full h-full flex-grow flex flex-col m-0 p-0 rounded-none border-0 max-w-none">
			<div 
				bind:this={messagesContainer}
				class="flex-grow overflow-y-auto p-4 bg-gray-50 dark:bg-gray-800"
				style="min-height: 200px; max-height: calc(100vh - 200px);"
			>
				{#if messages.length === 0}
					<div class="text-center text-gray-500 dark:text-gray-400 py-8">
						<MessagesSolid class="w-12 h-12 mx-auto mb-2" />
						<p>Start a conversation with the LLM!</p>
					</div>
				{:else}
					{#each messages as message}
						<div class="mb-4 {message.isUser ? 'text-right' : ''}">
							<div 
								class="inline-block rounded-lg px-4 py-2 max-w-[90%] text-left {
									message.isUser 
										? 'bg-primary-600 text-white' 
										: 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-white'
								}"
							>
								{#if message.isUser}
									{message.text}
								{:else}
									<div class="markdown-content">
										<SvelteMarkdown source={message.text} />
									</div>
								{/if}
							</div>
						</div>
					{/each}
					
					{#if isLoading}
						<div class="flex items-center justify-start mb-4">
							<div class="inline-block rounded-lg px-4 py-2 bg-gray-200 dark:bg-gray-700">
								<Spinner size="4" class="mr-2" />
								<span>AI is thinking...</span>
							</div>
						</div>
					{/if}
					
					{#if error}
						<div class="mb-4">
							<div class="inline-block rounded-lg px-4 py-2 bg-red-100 text-red-800 dark:bg-red-800 dark:text-red-100">
								{error}
							</div>
						</div>
					{/if}
				{/if}
			</div>
			
			<div class="flex flex-col p-2 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 sticky bottom-0">
				<!-- Realm data toggle -->
				<div class="flex items-center mb-2">
					<Toggle bind:checked={includeRealmData} size="small" />
					<span class="ml-2 text-sm text-gray-700 dark:text-gray-300 flex items-center">
						<DatabaseSolid class="w-4 h-4 mr-1" />
						Include realm data
						{#if isLoadingRealmData}
							<Spinner size="4" class="ml-2" />
						{/if}
					</span>
					{#if includeRealmData && !realmData && !isLoadingRealmData}
						<Button size="xs" color="light" class="ml-2" on:click={fetchRealmData}>Fetch Data</Button>
					{/if}
				</div>
				
				<!-- Message input -->
				<div class="flex">
					<Textarea
						class="flex-grow resize-none rounded-r-none"
						placeholder="Type your message..."
						rows="2"
						bind:value={newMessage}
						on:keydown={handleKeydown}
					/>
					<Button 
						color="primary" 
						class="rounded-l-none"
						disabled={isLoading || !newMessage.trim()}
						on:click={sendMessage}
					>
						<PaperPlaneSolid class="w-5 h-5" />
					</Button>
				</div>
			</div>
		</Card>
	</div>
</div> 

<style>
	.markdown-content :global(h1) {
		font-size: 1.8rem;
		font-weight: 700;
		margin: 1rem 0;
		color: inherit;
	}
	
	.markdown-content :global(h2) {
		font-size: 1.5rem;
		font-weight: 700;
		margin: 0.8rem 0;
		color: inherit;
	}
	
	.markdown-content :global(h3) {
		font-size: 1.25rem;
		font-weight: 600;
		margin: 0.6rem 0;
		color: inherit;
	}
	
	.markdown-content :global(ul) {
		list-style-type: disc !important;
		margin: 0.5rem 0 !important;
		padding-left: 2rem !important;
	}
	
	.markdown-content :global(ol) {
		list-style-type: decimal !important;
		margin: 0.5rem 0 !important;
		padding-left: 2rem !important;
	}
	
	.markdown-content :global(li) {
		display: list-item !important;
		margin: 0.25rem 0 !important;
	}
	
	.markdown-content :global(p) {
		margin: 0.5rem 0 !important;
	}
	
	.markdown-content :global(code) {
		font-family: monospace;
		background-color: rgba(0, 0, 0, 0.1);
		padding: 0.1rem 0.2rem;
		border-radius: 0.2rem;
	}
	
	.markdown-content :global(pre) {
		background-color: rgba(0, 0, 0, 0.1);
		padding: 0.5rem;
		border-radius: 0.3rem;
		overflow-x: auto;
		margin: 0.5rem 0;
	}
	
	.markdown-content :global(blockquote) {
		border-left: 3px solid #ccc;
		padding-left: 0.8rem;
		margin: 0.5rem 0 0.5rem 0.5rem;
		color: #555;
	}
</style> 